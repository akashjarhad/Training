"""
app/records.py
Core record processing module for AapleSeva Notified Services.
Provides functions to load, search, count, and retrieve service records.
"""

import json
from pathlib import Path


def get_default_data_path() -> Path:
    """Return default path to sample_records.json."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "sample_records.json"


def load_records(file_path: str | Path | None = None) -> list[dict]:
    """
    Load notified service records from a JSON file.
    Falls back to data.sample_records Python module if JSON file is missing.
    """
    if file_path is None:
        target_path = get_default_data_path()
    else:
        target_path = Path(file_path)

    if target_path.exists():
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback to importing SERVICES directly
    try:
        from data.sample_records import SERVICES
        return list(SERVICES)
    except ImportError:
        return []


def search(records: list[dict], keyword: str) -> list[dict]:
    """
    Perform a case-insensitive search across service records.
    Searches in service_name, category, department, designated_officer,
    and appellate officers.
    """
    if not keyword or not keyword.strip():
        return records

    kw = keyword.strip().lower()
    matches = []

    for r in records:
        searchable_values = [
            str(r.get("service_name", "")),
            str(r.get("category", "")),
            str(r.get("department", "")),
            str(r.get("designated_officer", "")),
            str(r.get("first_appellate_officer", "")),
            str(r.get("second_appellate_officer", "")),
        ]
        if any(kw in val.lower() for val in searchable_values):
            matches.append(r)

    return matches


def count_by(records: list[dict], field: str = "category") -> dict[str, int]:
    """
    Count records grouped by a specified field (default: 'category').
    Returns a dictionary of {field_value: count}.
    """
    counts: dict[str, int] = {}
    for r in records:
        val = str(r.get(field, "Unknown"))
        counts[val] = counts.get(val, 0) + 1
    return counts


def get_by_id(records: list[dict], record_id: int | str) -> dict | None:
    """
    Retrieve a service record by its unique ID.
    Handles both integer and string IDs.
    Returns the matching record dict or None if not found.
    """
    try:
        numeric_id = int(record_id)
    except (ValueError, TypeError):
        return None

    for r in records:
        if r.get("id") == numeric_id:
            return r

    return None

