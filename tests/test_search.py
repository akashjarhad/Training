"""
tests/test_search.py
Tests for semantic search (chunking, embedding, vector store).
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from app.chunking import chunk_documents
from app.embed import search


def test_chunk_documents():
    """Test document chunking produces valid chunks with metadata."""
    # Create a simple test document
    docs = [
        {
            "source": "test.pdf",
            "title": "Test Document",
            "pages": [
                {"page_num": 1, "text": "This is a test. " * 100},  # ~1600 chars
            ],
        }
    ]
    
    chunks = chunk_documents(
        docs,
        chunk_size=500,
        chunk_overlap=50,
    )
    
    assert len(chunks) > 0
    assert all("text" in c for c in chunks)
    assert all("source" in c for c in chunks)
    assert all("title" in c for c in chunks)
    assert all("page" in c for c in chunks)
    
    # Check chunk sizes
    for chunk in chunks:
        assert len(chunk["text"]) <= 600  # chunk_size + overlap margin


def test_semantic_search():
    """Test semantic search returns relevant results."""
    # This requires the vector DB to be initialized
    # We'll use a simple query and check structure
    results = search("caste certificate", n_results=3)
    
    assert isinstance(results, list)
    # If DB is empty, should return empty list
    if len(results) > 0:
        assert all("text" in r for r in results)
        assert all("distance" in r for r in results)
        assert all("title" in r for r in results)


def test_semantic_search_returns_limited_results():
    """Test semantic search respects n_results parameter."""
    results = search("time limit", n_results=2)
    
    assert isinstance(results, list)
    # Should return at most 2 results
    assert len(results) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
