"""
tests/test_records.py
Unit tests for app.records module.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.records import load_records, search, count_by, get_by_id


def test_load_records():
    records = load_records()
    assert isinstance(records, list)
    assert len(records) == 20
    assert records[0]["service_name"] == "Age, Nationality and Domicile Certificate"


def test_search_by_keyword():
    records = load_records()
    results = search(records, "caste")
    assert len(results) >= 1
    assert any("Caste" in r["service_name"] for r in results)


def test_count_by_category():
    records = load_records()
    counts = count_by(records, "category")
    assert isinstance(counts, dict)
    assert sum(counts.values()) == 20
    assert "Certificates" in counts
    assert "Land Records" in counts


def test_get_by_id():
    records = load_records()
    # Test valid int ID
    rec1 = get_by_id(records, 1)
    assert rec1 is not None
    assert rec1["id"] == 1
    assert "Domicile" in rec1["service_name"]

    # Test valid str ID
    rec2 = get_by_id(records, "2")
    assert rec2 is not None
    assert rec2["id"] == 2
    assert "Income" in rec2["service_name"]

    # Test invalid ID
    assert get_by_id(records, 999) is None
    assert get_by_id(records, "abc") is None


if __name__ == "__main__":
    test_load_records()
    test_search_by_keyword()
    test_count_by_category()
    test_get_by_id()
    print("All unit tests passed successfully!")
