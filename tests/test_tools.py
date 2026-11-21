"""
tests/test_tools.py
Tests for agent tools: rag_search and rts_due_date.
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import os
import pytest
from datetime import datetime, timedelta

# Set mock mode for LLM calls
os.environ["LLM_MOCK"] = "1"

from app.tools import rag_search, rts_due_date, _parse_date, _add_working_days, HOLIDAY_DATES


def test_rag_search_tool():
    """Test rag_search tool returns valid structure."""
    result = rag_search("What is the Right to Service Act?")
    
    assert "answer" in result
    assert "sources" in result
    assert "retrieved_count" in result
    assert "question" in result
    assert isinstance(result["sources"], list)


def test_rag_search_with_top_k():
    """Test rag_search respects top_k parameter."""
    result = rag_search("time limit", top_k=3)
    
    assert "retrieved_count" in result
    # Should retrieve at most 3 chunks
    assert result["retrieved_count"] <= 3


def test_rts_due_date_valid_service():
    """Test rts_due_date calculates due date for valid service."""
    result = rts_due_date(
        service_name="caste certificate",
        application_date="2026-11-01",
    )
    
    assert result["error"] is None
    assert "due_date" in result
    assert "days_until_due" in result
    assert "is_late" in result
    assert "time_limit_days" in result
    assert result["application_date"] == "2026-11-01"


def test_rts_due_date_calendar_days():
    """Test rts_due_date uses calendar days by default."""
    result = rts_due_date(
        service_name="domicile",
        application_date="2026-11-01",
        count_working_days=False,
    )
    
    assert result["error"] is None
    assert result["working_days"] is False
    
    # Calculate expected due date
    if result["time_limit_days"]:
        app_date = datetime(2026, 11, 1).date()
        expected_due = app_date + timedelta(days=result["time_limit_days"])
        assert result["due_date"] == expected_due.isoformat()


def test_rts_due_date_working_days():
    """Test rts_due_date excludes weekends and holidays."""
    result = rts_due_date(
        service_name="income certificate",
        application_date="2026-11-01",
        count_working_days=True,
    )
    
    assert result["error"] is None
    assert result["working_days"] is True


def test_rts_due_date_invalid_date():
    """Test rts_due_date handles invalid date format."""
    result = rts_due_date(
        service_name="caste",
        application_date="invalid-date",
    )
    
    assert "error" in result
    assert result["error"] is not None
    assert "Invalid application_date" in result["error"]


def test_rts_due_date_unknown_service():
    """Test rts_due_date handles unknown service name."""
    result = rts_due_date(
        service_name="nonexistent service xyz",
        application_date="2026-11-01",
    )
    
    assert "error" in result
    assert result["error"] is not None
    assert "No service found" in result["error"]


def test_parse_date():
    """Test _parse_date helper function."""
    # Test YYYY-MM-DD format
    date1 = _parse_date("2026-11-01")
    assert date1.year == 2026
    assert date1.month == 11
    assert date1.day == 1
    
    # Test ISO format with time
    date2 = _parse_date("2026-11-01T10:30:00")
    assert date2.year == 2026
    assert date2.month == 11
    assert date2.day == 1


def test_parse_date_invalid():
    """Test _parse_date raises ValueError for invalid input."""
    with pytest.raises(ValueError):
        _parse_date("not-a-date")


def test_add_working_days():
    """Test _add_working_days skips weekends and holidays."""
    # Start on Friday Nov 20, 2026
    start = datetime(2026, 11, 20).date()  # Friday
    
    # Add 1 working day -> should skip weekend to Monday Nov 23
    result = _add_working_days(start, 1)
    assert result == datetime(2026, 11, 23).date()
    
    # Add 5 working days -> should be one week later (Nov 27)
    result = _add_working_days(start, 5)
    assert result == datetime(2026, 11, 27).date()


def test_holiday_dates_loaded():
    """Test that holiday dates are loaded correctly."""
    assert len(HOLIDAY_DATES) > 0
    
    # Check a known holiday (Republic Day 2026)
    republic_day = datetime(2026, 1, 26).date()
    assert republic_day in HOLIDAY_DATES
    
    # Check that holidays are date objects
    for holiday in HOLIDAY_DATES:
        assert isinstance(holiday, datetime(2026, 1, 1).date().__class__)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
