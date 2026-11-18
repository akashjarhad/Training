"""
app/tools.py
Agent tools for AapleSeva: RAG search and due date calculation.

Tools provided:
    - rag_search: Semantic search over documents with LLM-generated answers
    - rts_due_date: Calculate service delivery due date from application date

These tools are designed for use by both the hand-written agent loop 
(app/agent_loop.py) and the LangGraph agent (app/graph.py).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.rag import answer_question
from app.records import load_records


# Maharashtra public holidays 2026-2027 (for working day calculations)
# Source: Government of Maharashtra General Administration Department
HOLIDAYS_2026 = [
    "2026-01-26",  # Republic Day
    "2026-03-01",  # Maha Shivratri
    "2026-03-25",  # Holi
    "2026-04-02",  # Gudi Padwa
    "2026-04-06",  # Ram Navami
    "2026-04-14",  # Ambedkar Jayanti / Mahavir Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-07-17",  # Eid al-Adha (Bakri Id)
    "2026-08-15",  # Independence Day
    "2026-08-22",  # Janmashtami
    "2026-09-05",  # Ganesh Chaturthi
    "2026-10-02",  # Gandhi Jayanti
    "2026-10-24",  # Dussehra
    "2026-11-13",  # Diwali
    "2026-12-25",  # Christmas
]

HOLIDAYS_2027 = [
    "2027-01-26",  # Republic Day
    "2027-02-18",  # Maha Shivratri
    "2027-03-15",  # Holi
    "2027-03-23",  # Gudi Padwa
    "2027-03-27",  # Ram Navami
    "2027-04-14",  # Ambedkar Jayanti
    "2027-05-01",  # Maharashtra Day
    "2027-07-07",  # Eid al-Adha
    "2027-08-11",  # Janmashtami
    "2027-08-15",  # Independence Day
    "2027-08-26",  # Ganesh Chaturthi
    "2027-10-02",  # Gandhi Jayanti
    "2027-10-13",  # Dussehra
    "2027-11-02",  # Diwali
    "2027-12-25",  # Christmas
]

# Combine into a set of datetime.date objects for fast lookup
HOLIDAY_DATES = {
    datetime.fromisoformat(d).date() 
    for d in HOLIDAYS_2026 + HOLIDAYS_2027
}


def rag_search(question: str, top_k: int = 5) -> dict[str, Any]:
    """
    RAG tool: answer a question using semantic search + LLM.
    
    Retrieves relevant document chunks and generates a grounded answer
    with source citations. The LLM is instructed to say "I don't know"
    when the retrieved context lacks the answer.
    
    Args:
        question: User's question about AapleSeva/RTS Act
        top_k: Number of document chunks to retrieve (default 5)
    
    Returns:
        {
            "answer": str,          # LLM's response with citations
            "sources": list[dict],  # [{title, page, source, distance}, ...]
            "retrieved_count": int,
            "question": str
        }
    
    Example:
        >>> result = rag_search("What is the time limit for caste certificate?")
        >>> print(result["answer"])
        "The time limit is 21 days [RTS Notified Services, page 3]"
    """
    try:
        result = answer_question(question=question, top_k=top_k)
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "retrieved_count": result["retrieved_count"],
            "question": result["question"],
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "answer": f"Error performing RAG search: {exc}",
            "sources": [],
            "retrieved_count": 0,
            "question": question,
        }


def rts_due_date(
    service_name: str,
    application_date: str,
    count_working_days: bool = False,
) -> dict[str, Any]:
    """
    Calculate the statutory due date for an RTS service application.
    
    Looks up the service's time limit in records.json and adds it to the
    application date. Returns the due date and whether the service is late.
    
    Args:
        service_name: Name of the service (fuzzy matched against records)
        application_date: Date application was submitted (YYYY-MM-DD or ISO format)
        count_working_days: If True, exclude weekends and holidays; 
                           if False, use calendar days (default)
    
    Returns:
        {
            "service_name": str,        # Matched service name
            "service_id": int,          # Record ID
            "time_limit_days": int,     # Statutory time limit
            "application_date": str,    # Input date (normalized)
            "due_date": str,           # Calculated due date (YYYY-MM-DD)
            "days_until_due": int,      # Negative if overdue
            "is_late": bool,           # True if past due date
            "working_days": bool,       # Whether working days were used
            "today": str,              # Reference date (YYYY-MM-DD)
            "error": str | None        # Error message if lookup failed
        }
    
    Example:
        >>> result = rts_due_date("caste certificate", "2026-11-01")
        >>> print(f"Due: {result['due_date']}, Late: {result['is_late']}")
        "Due: 2026-11-22, Late: False"
    """
    # Load records
    records = load_records()
    
    # Parse application date
    try:
        app_date = _parse_date(application_date)
    except ValueError as exc:
        return {
            "error": f"Invalid application_date: {exc}",
            "service_name": service_name,
            "application_date": application_date,
        }
    
    # Find matching service
    matched = _find_service(records, service_name)
    if not matched:
        return {
            "error": f"No service found matching '{service_name}'",
            "service_name": service_name,
            "application_date": application_date,
        }
    
    # Check if time limit is available
    time_limit = matched.get("time_limit_days")
    if time_limit is None:
        return {
            "error": f"Service '{matched['service_name']}' has no time_limit_days in records",
            "service_name": matched["service_name"],
            "service_id": matched.get("id"),
            "application_date": application_date,
            "time_limit_days": None,
        }
    
    # Calculate due date
    if count_working_days:
        due_date = _add_working_days(app_date, time_limit)
    else:
        due_date = app_date + timedelta(days=time_limit)
    
    # Check if late
    today = datetime.now().date()
    days_until = (due_date - today).days
    is_late = today > due_date
    
    return {
        "service_name": matched["service_name"],
        "service_id": matched.get("id"),
        "time_limit_days": time_limit,
        "time_limit_text": matched.get("time_limit_text"),
        "application_date": app_date.isoformat(),
        "due_date": due_date.isoformat(),
        "days_until_due": days_until,
        "is_late": is_late,
        "working_days": count_working_days,
        "today": today.isoformat(),
        "error": None,
    }


def _parse_date(date_str: str) -> datetime.date:
    """Parse a date string in YYYY-MM-DD or ISO format."""
    try:
        # Try ISO format first (handles datetime strings)
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.date()
    except ValueError:
        # Try simple date format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(
                f"Date must be YYYY-MM-DD format, got '{date_str}'"
            ) from exc


def _find_service(records: list[dict], query: str) -> dict | None:
    """
    Find a service by fuzzy name match.
    
    Returns the first record where query (case-insensitive) appears in 
    service_name or department. Prioritizes records with time_limit_days.
    """
    query_lower = query.lower()
    
    # First pass: records with time_limit_days
    for record in records:
        if not record.get("time_limit_days"):
            continue
        name = record.get("service_name", "").lower()
        dept = record.get("department", "").lower()
        if query_lower in name or query_lower in dept:
            return record
    
    # Second pass: any matching record
    for record in records:
        name = record.get("service_name", "").lower()
        dept = record.get("department", "").lower()
        if query_lower in name or query_lower in dept:
            return record
    
    return None


def _add_working_days(start_date: datetime.date, num_days: int) -> datetime.date:
    """
    Add working days to a date, skipping weekends and holidays.
    
    A working day is Monday-Friday, excluding Maharashtra public holidays.
    """
    current = start_date
    days_added = 0
    
    while days_added < num_days:
        current += timedelta(days=1)
        # Check if it's a working day (Mon-Fri, not a holiday)
        if current.weekday() < 5 and current not in HOLIDAY_DATES:
            days_added += 1
    
    return current


# Tool metadata for LangGraph/LangChain integration
TOOL_DEFINITIONS = [
    {
        "name": "rag_search",
        "description": (
            "Search AapleSeva documents and answer questions using RAG. "
            "Use this when the user asks about RTS Act provisions, service details, "
            "time limits, appellate procedures, or any policy question. "
            "The LLM provides answers with document citations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The user's question about AapleSeva/RTS Act",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of document chunks to retrieve (default 5)",
                    "default": 5,
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "rts_due_date",
        "description": (
            "Calculate the statutory due date for an RTS service application. "
            "Use this when the user wants to know when their service should be delivered, "
            "or to check if a service is overdue. Requires the service name and "
            "application submission date."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the RTS service (e.g., 'caste certificate', 'water connection')",
                },
                "application_date": {
                    "type": "string",
                    "description": "Date application was submitted (YYYY-MM-DD format)",
                },
                "count_working_days": {
                    "type": "boolean",
                    "description": "If true, exclude weekends and holidays; if false use calendar days (default false)",
                    "default": False,
                },
            },
            "required": ["service_name", "application_date"],
        },
    },
]


def get_tool_function(name: str):
    """Get the Python function for a tool by name."""
    tools = {
        "rag_search": rag_search,
        "rts_due_date": rts_due_date,
    }
    return tools.get(name)
