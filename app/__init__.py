"""
app package for AapleSeva Citizen Services.
"""
from app.records import load_records, search, count_by, get_by_id
from app.models import Record

__all__ = ["load_records", "search", "count_by", "get_by_id", "Record"]
