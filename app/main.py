"""
app/main.py
FastAPI service for AapleSeva notified services.

Run it with uvicorn (from the project root)::

    python -m uvicorn app.main:app --reload

Endpoints
---------
- GET  /health            -> service liveness check
- GET  /records?limit=N    -> list records, optionally capped with ``limit``
- GET  /records/{id}       -> one record, 404 when the id is unknown
- GET  /search?q=...       -> TF-IDF + cosine ranking that powers smart search
- POST /questions          -> submit a citizen question (persisted to a JSON file)
- POST /chat               -> ask the AapleSeva LLM assistant (answer, confidence, follow_up)
- POST /ask                -> RAG endpoint: answer with document chunk citations
- POST /agent              -> LangGraph agent with tools (rag_search, rts_due_date) and memory
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.llm import get_provider
from app.records import get_by_id, load_records
from app.smart_search import SmartSearch
from app.rag import answer_question
from app.graph import create_agent_graph, run_agent_graph
from app.graph import create_agent_graph, run_agent_graph


app = FastAPI(
    title="AapleSeva Citizen Services API",
    description=(
        "HTTP service over the AapleSeva notified services dataset, exposing "
        "record lookup, smart (TF-IDF) search, a citizen question endpoint, and "
        "an LLM chat assistant."
    ),
    version="1.0.0",
)

# Load the record set once at import time and build the search index once.
# load_records() defaults to data/sample_records.json (the 20 rich Revenue
# Department services); pass a path to point it at data/records.json instead.
RECORDS: list[dict] = load_records()
SEARCH: SmartSearch = SmartSearch(RECORDS)

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "questions.json"


# --------------------------------------------------------------------------- #
# Request / response models
# --------------------------------------------------------------------------- #
class QuestionCreate(BaseModel):
    """Body for ``POST /questions``."""

    question: str = Field(..., min_length=1, description="The citizen's question.")
    name: str | None = Field(default=None, description="Optional submitter name.")
    service_id: int | None = Field(
        default=None,
        description="Optional id of the service the question is about.",
    )


class ChatRequest(BaseModel):
    """Body for ``POST /chat``."""

    question: str = Field(..., min_length=1, description="The citizen's question.")
    provider: str | None = Field(
        default=None, description="groq or gemini; defaults to LLM_PROVIDER env."
    )
    top_k: int = Field(
        default=5, ge=1, le=20, description="Records to retrieve as context."
    )
    prompt_version: Literal["v1", "v2"] = Field(
        default="v1", description="Which task prompt to use."
    )


class AskRequest(BaseModel):
    """Body for ``POST /ask`` (RAG endpoint)."""

    question: str = Field(..., min_length=1, description="User question")
    top_k: int = Field(5, ge=1, le=20, description="Number of chunks to retrieve")
    provider: str | None = Field(None, description="LLM provider (groq/gemini)")
    temperature: float = Field(0.2, ge=0.0, le=1.0, description="LLM temperature")


class AgentRequest(BaseModel):
    """Body for ``POST /agent`` (LangGraph agent endpoint)."""

    query: str = Field(..., min_length=1, description="User query")
    conversation_history: list[dict] | None = Field(
        None, description="Previous messages for conversation memory"
    )


# --------------------------------------------------------------------------- #
# Question persistence (plain JSON file, fine for a demo service)
# --------------------------------------------------------------------------- #
def _load_questions() -> list[dict]:
    if QUESTIONS_PATH.exists():
        with open(QUESTIONS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    return []


def _save_questions(questions: list[dict]) -> None:
    QUESTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUESTIONS_PATH, "w", encoding="utf-8") as fh:
        json.dump(questions, fh, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Chat (LLM) helpers
# --------------------------------------------------------------------------- #
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    """Read ``prompts/<name>.md`` as raw text."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise HTTPException(
            status_code=500, detail=f"prompt file not found: {path.name}"
        )
    return path.read_text(encoding="utf-8")


def _fill_prompt(template: str, context: str, question: str) -> str:
    """Replace ``{context}`` and ``{question}`` placeholders.

    Uses ``str.replace`` rather than ``str.format`` so the prompt template may
    contain literal JSON braces (e.g. example output) without escaping.
    """
    return template.replace("{context}", context).replace("{question}", question)


def _records_to_context(records: list[dict]) -> str:
    """Render retrieved records as compact JSON for the LLM context window."""
    rows = [
        {
            "id": r.get("id"),
            "service_name": r.get("service_name"),
            "department": r.get("department"),
            "category": r.get("category"),
            "time_limit_days": r.get("time_limit_days"),
            "designated_officer": r.get("designated_officer"),
            "first_appellate_officer": r.get("first_appellate_officer"),
            "source_url": r.get("source_url"),
        }
        for r in records
    ]
    return json.dumps(rows, ensure_ascii=False, indent=2) if rows else "[]"


def _extract_json(text: str) -> dict:
    """Tolerantly pull a JSON object out of an LLM response.

    Handles code-fenced output and extra prose around the JSON; returns ``{}``
    if no parseable object is found.
    """
    if not text:
        return {}
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return {}


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health", summary="Liveness check")
def health() -> dict:
    """Return ``status: ok`` plus the number of loaded records."""
    return {"status": "ok", "service": "AapleSeva", "records": len(RECORDS)}


@app.get("/records", summary="List notified service records")
def list_records(
    limit: int | None = Query(default=None, ge=1, le=1000),
) -> dict:
    """Return every record, or the first ``limit`` when one is supplied."""
    selected = RECORDS if limit is None else RECORDS[:limit]
    return {"count": len(selected), "records": selected}


@app.get("/records/{record_id}", summary="Fetch one record by id")
def get_record(record_id: int) -> dict:
    """Return a single record. Responds with ``404`` when the id is unknown."""
    record = get_by_id(RECORDS, record_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"Record {record_id} not found"
        )
    return record


@app.get("/search", summary="Smart search over records")
def search_records(
    q: str = Query(default="", description="Free-text query."),
    top_k: int = Query(default=10, ge=1, le=100),
) -> dict:
    """Rank records by TF-IDF + cosine similarity to ``q``.

    An empty query returns every record unranked, mirroring the behaviour of
    the substring search used by the CLI.
    """
    if not q.strip():
        return {"query": q, "count": len(RECORDS), "results": RECORDS}

    ranked = SEARCH.rank(q, top_k=top_k)
    results = [
        {"score": round(score, 4), **record} for record, score in ranked
    ]
    return {"query": q, "count": len(results), "results": results}


@app.post("/questions", summary="Submit a citizen question")
def submit_question(payload: QuestionCreate) -> dict:
    """Persist a question to ``data/questions.json`` and return the stored copy.

    When ``service_id`` is supplied it must reference an existing record, else
    this responds with ``404``.
    """
    if payload.service_id is not None and get_by_id(RECORDS, payload.service_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"service_id {payload.service_id} does not match any record",
        )

    questions = _load_questions()
    new_id = (max((q["id"] for q in questions), default=0)) + 1
    stored = {
        "id": new_id,
        "question": payload.question,
        "name": payload.name,
        "service_id": payload.service_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    questions.append(stored)
    _save_questions(questions)
    return {"status": "accepted", "question": stored}


@app.post("/chat", summary="Ask the AapleSeva assistant a question")
def chat(payload: ChatRequest) -> dict:
    """Answer a citizen question with an LLM, grounded in retrieved records.

    Retrieves the top records for the question (RAG), fills the chosen task
    prompt with them, calls the configured LLM provider, and returns the
    parsed JSON: ``answer``, ``confidence`` and ``follow_up``.
    """
    try:
        provider = get_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ranked = SEARCH.rank(payload.question, top_k=payload.top_k)
    retrieved = [record for record, _ in ranked]
    context = _records_to_context(retrieved)

    system = _load_prompt("system")
    task = _load_prompt(f"task_answer_{payload.prompt_version}")
    user_content = _fill_prompt(task, context=context, question=payload.question)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    try:
        llm_resp = provider.chat(messages)
    except Exception as exc:  # network / auth / provider errors
        raise HTTPException(
            status_code=502,
            detail=f"LLM call failed: {exc}. Set LLM_MOCK=1 for offline testing.",
        )

    parsed = _extract_json(llm_resp.text)
    return {
        "answer": parsed.get("answer", llm_resp.text),
        "confidence": parsed.get("confidence", "unknown"),
        "follow_up": parsed.get("follow_up", ""),
        "provider": llm_resp.provider,
        "model": llm_resp.model,
        "mock": llm_resp.mock,
        "prompt_version": payload.prompt_version,
        "retrieved": [r.get("id") for r in retrieved],
    }


@app.post("/ask", summary="RAG endpoint: answer with document citations")
def ask(payload: AskRequest) -> dict:
    """
    RAG endpoint: answer questions using retrieved document chunks + LLM.
    
    Retrieves top-k relevant chunks via semantic search, sends them with the
    question to an LLM, and returns the answer with source citations.
    
    The LLM is instructed to:
    - Cite sources by [Document Title, page X]
    - Say "I don't know" when context lacks answer
    - Answer from context only, no external knowledge
    
    Returns:
        - question: the input question
        - answer: LLM's response with citations
        - sources: list of {title, page, source, distance}
        - retrieved_count: number of chunks retrieved
        - provider: LLM provider used
        - model: LLM model used
        - mock: whether response was mocked
    """
    try:
        result = answer_question(
            question=payload.question,
            top_k=payload.top_k,
            provider=payload.provider,
            temperature=payload.temperature,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"RAG query failed: {exc}",
        )


@app.post("/agent", summary="LangGraph agent with tools and memory")
def agent(payload: AgentRequest) -> dict:
    """
    LangGraph agent endpoint: autonomous agent with tools and conversation memory.
    
    The agent can:
    - Use rag_search tool for policy/document questions
    - Use rts_due_date tool for calculating service delivery deadlines
    - Remember conversation context across multiple turns
    - Request approval before executing tools (human-in-the-loop)
    
    Request body:
        {
            "query": "What is the time limit for caste certificate?",
            "conversation_history": [  // optional, for multi-turn conversations
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }
    
    Response:
        {
            "query": str,
            "answer": str,              # Final answer from agent
            "messages": list[dict],     # Full conversation history
            "tool_calls": list[dict],   # Tools that were executed
            "conversation_id": str      # For tracking multi-turn conversations
        }
    """
    try:
        # Create agent graph (cached in production)
        graph = create_agent_graph()
        
        # Run agent
        result = run_agent_graph(
            graph=graph,
            query=payload.query,
            conversation_history=payload.conversation_history,
        )
        
        return {
            "query": payload.query,
            "answer": result["final_answer"],
            "messages": result["messages"],
            "tool_calls": result["tool_calls"],
            "conversation_id": None,  # TODO: implement session management
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {exc}",
        )
