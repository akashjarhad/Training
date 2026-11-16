"""
app/vectorstore.py
FastAPI server exposing semantic search over the AapleSeva document index.

Starts a local HTTP API:
    GET /search/semantic?q=your+query&top_k=5

Returns JSON with the top-k most relevant chunks, each carrying source, page,
title and distance.

Run the server:
    python -m app.vectorstore
    # or with uvicorn for auto-reload:
    uvicorn app.vectorstore:app --reload --port 8000

Before starting the server, index the chunks:
    python -m app.embed --index
"""

from __future__ import annotations

import sys
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from app.embed import search as semantic_search, get_collection

app = FastAPI(
    title="AapleSeva Semantic Search",
    description="Search Right to Service documents by meaning, not keywords.",
    version="0.1.0",
)


@app.get("/")
def root():
    """Health check and API info."""
    try:
        collection = get_collection()
        count = collection.count()
    except Exception:
        count = -1

    return {
        "service": "AapleSeva Semantic Search API",
        "version": "0.1.0",
        "endpoints": {
            "search": "/search/semantic?q=<query>&top_k=5",
            "health": "/health",
        },
        "collection_count": count,
    }


@app.get("/health")
def health():
    """Check if the vector store is accessible."""
    try:
        collection = get_collection()
        count = collection.count()
        return {"status": "ok", "collection_count": count}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "error": str(exc)},
        )


@app.get("/search/semantic")
def search_semantic(
    q: str = Query(..., description="Search query", min_length=1),
    top_k: int = Query(5, ge=1, le=20, description="Number of results to return"),
) -> dict[str, Any]:
    """
    Semantic search endpoint.

    Returns the top-k chunks most similar to the query, ordered by relevance
    (ascending distance).
    """
    if not q.strip():
        return {"query": q, "hits": [], "count": 0}

    try:
        hits = semantic_search(q, n_results=top_k)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "error": "search failed",
                "detail": str(exc),
                "query": q,
            },
        )

    return {
        "query": q,
        "hits": hits,
        "count": len(hits),
    }


def main():
    """Start the server using uvicorn."""
    import uvicorn

    print("Starting AapleSeva Semantic Search API")
    print("  Run 'python -m app.embed --index' first if collection is empty")
    print()

    uvicorn.run(
        "app.vectorstore:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
