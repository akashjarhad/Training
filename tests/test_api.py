"""
tests/test_api.py
Integration tests for FastAPI endpoints.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import os
import pytest
from fastapi.testclient import TestClient

# Set mock mode for LLM calls in tests
os.environ["LLM_MOCK"] = "1"

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test GET /health returns service status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "AapleSeva"
    assert "records" in data
    assert data["records"] > 0


def test_list_records():
    """Test GET /records returns all records."""
    response = client.get("/records")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "records" in data
    assert data["count"] == len(data["records"])
    assert data["count"] > 0


def test_list_records_with_limit():
    """Test GET /records?limit=5 returns limited results."""
    response = client.get("/records?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert len(data["records"]) == 5


def test_get_single_record():
    """Test GET /records/{id} returns one record."""
    response = client.get("/records/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "service_name" in data
    assert "department" in data


def test_get_nonexistent_record():
    """Test GET /records/{id} returns 404 for unknown ID."""
    response = client.get("/records/99999")
    assert response.status_code == 404


def test_search_endpoint():
    """Test GET /search?q=caste performs TF-IDF search."""
    response = client.get("/search?q=caste")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "caste"
    assert data["count"] > 0
    assert "results" in data
    # Results should have scores
    if data["count"] > 0:
        assert "score" in data["results"][0]


def test_search_empty_query():
    """Test GET /search with empty query returns all records."""
    response = client.get("/search?q=")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == ""
    assert data["count"] > 0


def test_ask_endpoint_with_mock():
    """Test POST /ask (RAG) with mocked LLM."""
    payload = {
        "question": "What is the time limit for caste certificate?",
        "top_k": 5,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "retrieved_count" in data
    assert data["question"] == payload["question"]
    assert data["mock"] is True  # Should be mocked


def test_ask_endpoint_validation():
    """Test POST /ask validates required fields."""
    # Missing question
    response = client.post("/ask", json={})
    assert response.status_code == 422  # Validation error


def test_chat_endpoint_with_mock():
    """Test POST /chat with mocked LLM."""
    payload = {
        "question": "How do I apply for income certificate?",
        "top_k": 5,
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "confidence" in data
    assert "provider" in data
    assert data["mock"] is True


def test_submit_question():
    """Test POST /questions accepts and stores a question."""
    payload = {
        "question": "How long does it take?",
        "name": "Test User",
        "service_id": 1,
    }
    response = client.post("/questions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "question" in data
    assert data["question"]["question"] == payload["question"]
    assert data["question"]["name"] == payload["name"]
    assert "id" in data["question"]
    assert "created_at" in data["question"]


def test_submit_question_invalid_service():
    """Test POST /questions rejects invalid service_id."""
    payload = {
        "question": "Test question",
        "service_id": 99999,  # Non-existent
    }
    response = client.post("/questions", json=payload)
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
