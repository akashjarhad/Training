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
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.records import get_by_id, load_records
from app.smart_search import SmartSearch


app = FastAPI(
    title="AapleSeva Citizen Services API",
    description=(
        "HTTP service over the AapleSeva notified services dataset, exposing "
        "record lookup, smart (TF-IDF) search, and a citizen question endpoint."
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
