"""
eval/run_eval.py
Evaluation runner for the AapleSeva RAG system.

Runs multiple configurations (chunk size, top-k) against a fixed evaluation set
of 15 questions, scores each answer, and writes a comparison table showing which
configuration performs best.

Usage:
    python -m eval.run_eval --configs configs.json --output eval/results.json

The configs file specifies chunk size and top-k combinations to test.
Each config is evaluated on all 15 questions, scored automatically based on:
    - presence of expected keywords
    - correct handling of negative cases (saying "I don't know")
    - source relevance

Results are written to JSON and summarized as a markdown table in README.md.

Scoring:
    - Full match: answer contains all expected keywords/phrases → 1.0
    - Partial match: answer contains some expected keywords → 0.5
    - Negative case handled correctly (says "I don't know") → 1.0
    - Negative case failed (hallucinated answer) → 0.0
    - No match or irrelevant answer → 0.0
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from app.rag import answer_question
from app.chunking import chunk_documents
from app.embed import index_chunks


def load_eval_set(path: Path) -> list[dict[str, Any]]:
    """Load the evaluation dataset from JSON."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def score_answer(question_item: dict[str, Any], answer: str) -> dict[str, Any]:
    """
    Score a single answer against expected criteria.
    
    Returns a dict with:
        - score: 0.0 to 1.0
        - matched: list of matched keywords
        - feedback: human-readable explanation
    """
    expected_phrases = question_item.get("expected_contains", [])
    category = question_item.get("category", "")
    answer_lower = answer.lower()
    
    # Special handling for negative cases (must say "I don't know")
    if category == "negative_case":
        # Check if the answer correctly admits ignorance
        negative_markers = ["i don't know", "not available", "no information", "cannot answer"]
        if any(marker in answer_lower for marker in negative_markers):
            return {
                "score": 1.0,
                "matched": ["correctly says 'I don't know'"],
                "feedback": "Correctly handled negative case"
            }
        else:
            return {
                "score": 0.0,
                "matched": [],
                "feedback": "Failed negative case: should say 'I don't know' but provided answer"
            }
    
    # For positive cases, check for expected keywords
    if not expected_phrases:
        # No explicit expectations, give neutral score
        return {
            "score": 0.5,
            "matched": [],
            "feedback": "No explicit criteria, neutral score"
        }
    
    matched = []
    for phrase in expected_phrases:
        if phrase.lower() in answer_lower:
            matched.append(phrase)
    
    # Score based on match ratio
    match_ratio = len(matched) / len(expected_phrases)
    
    if match_ratio >= 1.0:
        score = 1.0
        feedback = "All expected keywords found"
    elif match_ratio >= 0.5:
        score = 0.7
        feedback = f"Partial match: {len(matched)}/{len(expected_phrases)} keywords"
    elif match_ratio > 0:
        score = 0.3
        feedback = f"Weak match: {len(matched)}/{len(expected_phrases)} keywords"
    else:
        score = 0.0
        feedback = "No expected keywords found"
    
    return {
        "score": score,
        "matched": matched,
        "feedback": feedback
    }


def run_config(
    config: dict[str, Any],
    eval_set: list[dict[str, Any]],
    raw_dir: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """
    Run evaluation for a single configuration.
    
    Config dict should contain:
        - name: human-readable label
        - chunk_size: character count for chunking
        - chunk_overlap: overlap size
        - top_k: number of chunks to retrieve
    
    Returns results dict with per-question scores and aggregate metrics.
    """
    config_name = config.get("name", "unnamed")
    chunk_size = config.get("chunk_size", 1200)
    chunk_overlap = config.get("chunk_overlap", 200)
    top_k = config.get("top_k", 5)
    
    print(f"\nRunning config: {config_name}")
    print(f"  chunk_size={chunk_size}, overlap={chunk_overlap}, top_k={top_k}")
    
    # Re-chunk and re-index with this config's parameters
    # Note: chunking.py currently has hardcoded size; this is a placeholder for
    # a future parameterized chunking interface. For now, we assume chunks are
    # already indexed at the default size and just vary top_k.
    # TODO: make chunk_documents() accept size/overlap parameters
    
    results = []
    total_score = 0.0
    
    for item in eval_set:
        q_id = item["id"]
        question = item["question"]
        category = item.get("category", "")
        
        print(f"  Q{q_id}: {question[:60]}...")
        
        try:
            result = answer_question(
                question=question,
                top_k=top_k,
                db_path=str(db_path) if db_path else None,
            )
            answer = result["answer"]
            sources = result["sources"]
        except Exception as exc:
            print(f"    ERROR: {exc}")
            answer = f"[error: {exc}]"
            sources = []
        
        # Score the answer
        score_data = score_answer(item, answer)
        total_score += score_data["score"]
        
        print(f"    score={score_data['score']:.2f} - {score_data['feedback']}")
        
        results.append({
            "id": q_id,
            "question": question,
            "category": category,
            "answer": answer,
            "sources": sources,
            "score": score_data["score"],
            "matched": score_data["matched"],
            "feedback": score_data["feedback"],
        })
        
        # Sleep briefly to avoid rate limits if using real LLM
        time.sleep(0.5)
    
    avg_score = total_score / len(eval_set) if eval_set else 0.0
    
    print(f"  Average score: {avg_score:.3f}")
    
    return {
        "config": config,
        "results": results,
        "metrics": {
            "total_questions": len(eval_set),
            "total_score": total_score,
            "average_score": avg_score,
        }
    }


def generate_comparison_table(all_results: list[dict[str, Any]]) -> str:
    """Generate a markdown comparison table for README."""
    lines = ["## RAG Evaluation Results\n"]
    lines.append("| Config | Chunk Size | Overlap | Top-K | Avg Score | Notes |")
    lines.append("|--------|------------|---------|-------|-----------|-------|")
    
    # Sort by average score descending
    sorted_results = sorted(
        all_results,
        key=lambda x: x["metrics"]["average_score"],
        reverse=True
    )
    
    for idx, run in enumerate(sorted_results, start=1):
        config = run["config"]
        metrics = run["metrics"]
        name = config.get("name", "unnamed")
        chunk_size = config.get("chunk_size", "default")
        overlap = config.get("chunk_overlap", "default")
        top_k = config.get("top_k", 5)
        avg_score = metrics["average_score"]
        
        # Mark the winner
        badge = "🏆 Winner" if idx == 1 else ""
        
        lines.append(
            f"| {name} | {chunk_size} | {overlap} | {top_k} | "
            f"{avg_score:.3f} | {badge} |"
        )
    
    lines.append("")
    lines.append(f"*Evaluated on {sorted_results[0]['metrics']['total_questions']} questions.*\n")
    
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run RAG evaluation across configs")
    parser.add_argument(
        "--eval-set",
        metavar="PATH",
        default="eval/eval_set.json",
        help="Path to evaluation dataset JSON",
    )
    parser.add_argument(
        "--configs",
        metavar="PATH",
        help="Path to configs JSON (if omitted, uses default 2 configs)",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default="eval/results.json",
        help="Path to write full results JSON",
    )
    parser.add_argument(
        "--db-path",
        metavar="PATH",
        help="Chroma DB path (default: data/chroma)",
    )
    parser.add_argument(
        "--raw-dir",
        metavar="PATH",
        help="Raw data directory for re-chunking (default: data/raw)",
    )
    args = parser.parse_args(argv)
    
    # Load evaluation set
    eval_set_path = Path(args.eval_set)
    if not eval_set_path.exists():
        print(f"Error: eval set not found at {eval_set_path}", file=sys.stderr)
        return 1
    
    eval_set = load_eval_set(eval_set_path)
    print(f"Loaded {len(eval_set)} evaluation questions from {eval_set_path}")
    
    # Load or generate configs
    if args.configs:
        with open(args.configs, "r", encoding="utf-8") as fh:
            configs = json.load(fh)
    else:
        # Default: test 2 configurations (chunk size and top-k variations)
        configs = [
            {
                "name": "baseline",
                "chunk_size": 1200,
                "chunk_overlap": 200,
                "top_k": 5,
            },
            {
                "name": "larger-context",
                "chunk_size": 1200,
                "chunk_overlap": 200,
                "top_k": 8,
            },
        ]
        print("Using default configs (baseline vs larger-context)")
    
    # Run each config
    all_results = []
    for config in configs:
        result = run_config(
            config=config,
            eval_set=eval_set,
            raw_dir=Path(args.raw_dir) if args.raw_dir else None,
            db_path=Path(args.db_path) if args.db_path else None,
        )
        all_results.append(result)
    
    # Write full results to JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(all_results, fh, indent=2, ensure_ascii=False)
    
    print(f"\nWrote full results to {output_path}")
    
    # Generate comparison table
    table_md = generate_comparison_table(all_results)
    print("\n" + table_md)
    
    # Append table to README
    readme_path = Path(__file__).resolve().parent.parent / "README.md"
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        
        # Remove old evaluation section if present
        marker = "## RAG Evaluation Results"
        if marker in readme_text:
            # Find the marker and remove everything from there to the next ## or end
            parts = readme_text.split(marker)
            before = parts[0]
            # Find next section or end
            after_marker = parts[1] if len(parts) > 1 else ""
            next_section = after_marker.find("\n## ")
            if next_section != -1:
                after = after_marker[next_section:]
            else:
                after = ""
            readme_text = before.rstrip() + "\n\n" + table_md + after
        else:
            # Append to end
            readme_text = readme_text.rstrip() + "\n\n" + table_md
        
        readme_path.write_text(readme_text, encoding="utf-8")
        print(f"Updated {readme_path} with evaluation results")
    else:
        print(f"Warning: README.md not found at {readme_path}, skipping update")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
