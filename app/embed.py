"""
app/embed.py
Semantic search over AapleSeva document chunks using sentence transformers.

Uses Chroma's default embedding function (all-MiniLM-L6-v2, 384-dimensional)
which is fast, runs locally, and good enough for retrieval over English +
Devanagari mixed documents.

    python -m app.embed                                # index all chunks
    python -m app.embed --search "time limit caste"    # search
    python -m app.embed --eval                          # run 10 test questions
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from app.chunking import chunk_documents, Chunk


def get_db_path(db_path=None) -> Path:
    """Return the directory holding the persistent Chroma collection."""
    if db_path:
        return Path(db_path)
    return Path(__file__).resolve().parent.parent / "data" / "chroma"


def get_collection(
    db_path=None, collection_name="aapleseva_docs"
) -> chromadb.Collection:
    """
    Open or create the persistent Chroma collection.

    Uses the default sentence-transformers/all-MiniLM-L6-v2 embedding function
    (384 dimensions). Chroma downloads the model on first use (~90 MB) and
    caches it locally.
    """
    path = get_db_path(db_path)
    path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(path))
    # Chroma's default is all-MiniLM-L6-v2, which is explicitly set here so
    # the collection schema is recorded in code.
    embed_fn = embedding_functions.DefaultEmbeddingFunction()

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embed_fn,
        metadata={"description": "AapleSeva Right to Service documents"},
    )
    return collection


def index_chunks(chunks: list[Chunk], db_path=None, batch_size=100) -> dict[str, Any]:
    """
    Index all chunks into the persistent Chroma collection.

    Chroma deduplicates by ID, so re-indexing the same chunks is safe (they
    overwrite rather than duplicate). Batch size 100 is Chroma's default and
    handles the ~1000 chunks comfortably.
    """
    if not chunks:
        raise ValueError("no chunks to index")

    collection = get_collection(db_path)

    # Clear existing data if we're re-indexing from scratch.
    existing = collection.count()
    if existing > 0:
        print(f"  clearing {existing} existing chunks", file=sys.stderr)
        collection.delete(where={})  # delete all

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        collection.add(
            ids=[c.id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[c.metadata() for c in batch],
        )

    return {
        "indexed": len(chunks),
        "collection_count": collection.count(),
        "sources": len({c.source for c in chunks}),
    }


def search(
    query: str, db_path=None, n_results=5, collection_name="aapleseva_docs"
) -> list[dict[str, Any]]:
    """
    Semantic search: return the top-k chunks most similar to the query.

    Returns a list of dicts, each with:
        id, text, source, page, title, source_url, distance

    Distance is cosine (lower = more similar); typical range 0.3–1.5 for
    hits, >1.5 for off-topic.
    """
    collection = get_collection(db_path, collection_name)
    if collection.count() == 0:
        print("  warning: collection is empty, run indexing first", file=sys.stderr)
        return []

    results = collection.query(query_texts=[query], n_results=n_results)

    hits: list[dict[str, Any]] = []
    if not results["ids"] or not results["ids"][0]:
        return hits

    for idx, chunk_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][idx] if results["metadatas"] else {}
        doc = results["documents"][0][idx] if results["documents"] else ""
        dist = results["distances"][0][idx] if results["distances"] else 0.0

        # Denormalise page back to None for non-paginated sources.
        page_raw = meta.get("page")
        page = page_raw if page_raw and page_raw != -1 else None

        hits.append(
            {
                "id": chunk_id,
                "text": doc,
                "source": meta.get("source", ""),
                "page": page,
                "title": meta.get("title", ""),
                "source_url": meta.get("source_url", ""),
                "distance": round(dist, 4),
            }
        )
    return hits


def run_eval_questions(db_path=None, questions_file=None, n_results=5) -> list[dict]:
    """
    Run semantic search for the 10 test questions and return results.

    Returns a list of dicts: {"question": ..., "hits": [...]}
    """
    if questions_file is None:
        questions_file = (
            Path(__file__).resolve().parent.parent / "eval" / "questions.txt"
        )
    else:
        questions_file = Path(questions_file)

    if not questions_file.exists():
        raise FileNotFoundError(f"{questions_file} not found")

    lines = questions_file.read_text(encoding="utf-8").splitlines()
    questions = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]

    results = []
    for q in questions:
        hits = search(q, db_path, n_results=n_results)
        results.append({"question": q, "hits": hits})
        print(f"  Q: {q}\n    => {len(hits)} hits")

    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Index AapleSeva chunks and search semantically."
    )
    parser.add_argument("--db-path", metavar="PATH")
    parser.add_argument(
        "--index",
        action="store_true",
        help="index all chunks (default if no other action)",
    )
    parser.add_argument("--search", metavar="QUERY", help="semantic search")
    parser.add_argument(
        "--eval", action="store_true", help="run 10 test questions and save results"
    )
    parser.add_argument("--top-k", type=int, default=5, metavar="N")
    parser.add_argument("--raw-dir", metavar="PATH", help="passed to chunking")
    args = parser.parse_args(argv)

    # Default action is to index if nothing else was requested.
    if not args.search and not args.eval:
        args.index = True

    if args.index:
        print("Indexing AapleSeva document chunks")
        try:
            chunks = chunk_documents(args.raw_dir)
        except FileNotFoundError as exc:
            print(f"  error: {exc}", file=sys.stderr)
            return 1

        if not chunks:
            print("  error: no chunks produced", file=sys.stderr)
            return 1

        report = index_chunks(chunks, args.db_path)
        print(f"  indexed {report['indexed']} chunks from {report['sources']} sources")
        print(f"  collection now holds {report['collection_count']} chunks")

    if args.search:
        hits = search(args.search, args.db_path, n_results=args.top_k)
        print(f"\nSearch: {args.search!r}\n")
        if not hits:
            print("  (no results)")
        for rank, hit in enumerate(hits, start=1):
            page_str = f" p{hit['page']}" if hit['page'] else ""
            print(f"{rank}. {hit['title']}{page_str}  [distance {hit['distance']}]")
            print(f"   {hit['text'][:200]}")
            print()

    if args.eval:
        print("\nRunning evaluation questions")
        try:
            results = run_eval_questions(args.db_path, n_results=args.top_k)
        except FileNotFoundError as exc:
            print(f"  error: {exc}", file=sys.stderr)
            return 1

        eval_dir = Path(__file__).resolve().parent.parent / "eval"
        eval_dir.mkdir(parents=True, exist_ok=True)
        out_path = eval_dir / "search_results.md"

        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("# Semantic Search Results\n\n")
            fh.write(
                f"Top-{args.top_k} chunks for each of the 10 test questions.\n\n"
            )
            fh.write("---\n\n")

            for item in results:
                fh.write(f"## Q: {item['question']}\n\n")
                if not item["hits"]:
                    fh.write("*(no results)*\n\n")
                    continue

                for rank, hit in enumerate(item["hits"], start=1):
                    page_str = f" (page {hit['page']})" if hit['page'] else ""
                    fh.write(f"**{rank}. {hit['title']}**{page_str}  \n")
                    fh.write(f"*Distance: {hit['distance']}*  \n")
                    fh.write(f"Source: `{hit['source']}`\n\n")
                    # Show first 300 chars of the chunk.
                    preview = hit["text"][:300]
                    if len(hit["text"]) > 300:
                        preview += "..."
                    fh.write(f"> {preview}\n\n")

        print(f"\n  wrote results -> {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
