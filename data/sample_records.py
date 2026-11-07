"""
data/sample_records.py
Revenue Department Notified Services under Maharashtra Right to Public Services Act (RTS Act, 2015).
Contains 20 of the most frequently used citizen services.
"""

import json
from pathlib import Path

SERVICES = [
    {
        "id": 1,
        "service_name": "Age, Nationality and Domicile Certificate",
        "department": "Revenue Department",
        "category": "Certificates",
        "time_limit_days": 15,
        "designated_officer": "Nayab Tahsildar",
        "first_appellate_officer": "Tahsildar",
        "second_appellate_officer": "Sub-Divisional Officer (SDO)",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 2,
        "service_name": "Income Certificate",
        "department": "Revenue Department",
        "category": "Certificates",
        "time_limit_days": 15,
        "designated_officer": "Nayab Tahsildar",
        "first_appellate_officer": "Tahsildar",
        "second_appellate_officer": "Sub-Divisional Officer (SDO)",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 3,
        "service_name": "Caste Certificate",
        "department": "Revenue Department",
        "category": "Certificates",
        "time_limit_days": 21,
        "designated_officer": "Sub-Divisional Officer (SDO) / Deputy Collector",
        "first_appellate_officer": "Additional Collector",
        "second_appellate_officer": "District Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 4,
        "service_name": "Non-Creamy Layer Certificate",
        "department": "Revenue Department",
        "category": "Certificates",
        "time_limit_days": 21,
        "designated_officer": "Sub-Divisional Officer (SDO) / Nayab Tahsildar",
        "first_appellate_officer": "Tahsildar",
        "second_appellate_officer": "Additional Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 5,
        "service_name": "Certified Copy of 7/12 Extract",
        "department": "Revenue Department",
        "category": "Land Records",
        "time_limit_days": 1,
        "designated_officer": "Talathi",
        "first_appellate_officer": "Circle Officer",
        "second_appellate_officer": "Tahsildar",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 6,
        "service_name": "Certified Copy of 8A Extract",
        "department": "Revenue Department",
        "category": "Land Records",
        "time_limit_days": 1,
        "designated_officer": "Talathi",
        "first_appellate_officer": "Circle Officer",
        "second_appellate_officer": "Tahsildar",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 7,
        "service_name": "Senior Citizen Certificate",
        "department": "Revenue Department",
        "category": "Social Welfare",
        "time_limit_days": 8,
        "designated_officer": "Nayab Tahsildar",
        "first_appellate_officer": "Tahsildar",
        "second_appellate_officer": "Sub-Divisional Officer (SDO)",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 8,
        "service_name": "Solvency Certificate",
        "department": "Revenue Department",
        "category": "Financial Services",
        "time_limit_days": 21,
        "designated_officer": "Tahsildar",
        "first_appellate_officer": "Sub-Divisional Officer (SDO)",
        "second_appellate_officer": "Additional Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 9,
        "service_name": "Small and Marginal Farmer Certificate",
        "department": "Revenue Department",
        "category": "Farmer Services",
        "time_limit_days": 15,
        "designated_officer": "Tahsildar",
        "first_appellate_officer": "Sub-Divisional Officer (SDO)",
        "second_appellate_officer": "Additional Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 10,
        "service_name": "Temporary Residence Certificate",
        "department": "Revenue Department",
        "category": "Certificates",
        "time_limit_days": 7,
        "designated_officer": "Nayab Tahsildar",
        "first_appellate_officer": "Tahsildar",
        "second_appellate_officer": "Sub-Divisional Officer (SDO)",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 11,
        "service_name": "Agriculturist Certificate",
        "department": "Revenue Department",
        "category": "Farmer Services",
        "time_limit_days": 15,
        "designated_officer": "Tahsildar",
        "first_appellate_officer": "Sub-Divisional Officer (SDO)",
        "second_appellate_officer": "Additional Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 12,
        "service_name": "Character Certificate",
        "department": "Revenue Department",
        "category": "Certificates",
        "time_limit_days": 15,
        "designated_officer": "Sub-Divisional Magistrate / Tahsildar",
        "first_appellate_officer": "Sub-Divisional Officer (SDO)",
        "second_appellate_officer": "Additional Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 13,
        "service_name": "Economically Weaker Section (EWS) Certificate",
        "department": "Revenue Department",
        "category": "Certificates",
        "time_limit_days": 15,
        "designated_officer": "Sub-Divisional Officer (SDO) / Tahsildar",
        "first_appellate_officer": "Additional Collector",
        "second_appellate_officer": "District Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 14,
        "service_name": "Legal Heir Certificate",
        "department": "Revenue Department",
        "category": "Financial Services",
        "time_limit_days": 21,
        "designated_officer": "Tahsildar",
        "first_appellate_officer": "Sub-Divisional Officer (SDO)",
        "second_appellate_officer": "Additional Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 15,
        "service_name": "Minority Certificate",
        "department": "Revenue Department",
        "category": "Social Welfare",
        "time_limit_days": 15,
        "designated_officer": "Sub-Divisional Officer (SDO) / Tahsildar",
        "first_appellate_officer": "Additional Collector",
        "second_appellate_officer": "District Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 16,
        "service_name": "Certified Copy of Mutation Entry",
        "department": "Revenue Department",
        "category": "Land Records",
        "time_limit_days": 5,
        "designated_officer": "Circle Officer",
        "first_appellate_officer": "Tahsildar",
        "second_appellate_officer": "Sub-Divisional Officer (SDO)",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 17,
        "service_name": "Attestation of Affidavit",
        "department": "Revenue Department",
        "category": "Certificates",
        "time_limit_days": 1,
        "designated_officer": "Executive Magistrate / Nayab Tahsildar",
        "first_appellate_officer": "Tahsildar",
        "second_appellate_officer": "Sub-Divisional Officer (SDO)",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 18,
        "service_name": "Land Valuation Certificate",
        "department": "Revenue Department",
        "category": "Land Records",
        "time_limit_days": 15,
        "designated_officer": "Tahsildar",
        "first_appellate_officer": "Sub-Divisional Officer (SDO)",
        "second_appellate_officer": "District Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 19,
        "service_name": "Permission for Non-Agricultural Assessment",
        "department": "Revenue Department",
        "category": "Land Records",
        "time_limit_days": 30,
        "designated_officer": "Sub-Divisional Officer (SDO) / Collector",
        "first_appellate_officer": "Additional Collector",
        "second_appellate_officer": "Divisional Commissioner",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    },
    {
        "id": 20,
        "service_name": "Public Event and Loudspeaker Permission",
        "department": "Revenue Department",
        "category": "General Administration",
        "time_limit_days": 5,
        "designated_officer": "Sub-Divisional Magistrate / Executive Magistrate",
        "first_appellate_officer": "Additional Collector",
        "second_appellate_officer": "District Collector",
        "source_url": "https://aaplesarkar.mahaonline.gov.in"
    }
]


def print_all_services(records):
    """Print all records formatted neatly."""
    print("=" * 85)
    print(f"{'ID':<4} | {'Service Name':<42} | {'Days':<5} | {'Designated Officer':<25}")
    print("-" * 85)
    for s in records:
        print(f"{s['id']:<4} | {s['service_name'][:42]:<42} | {s['time_limit_days']:<5} | {s['designated_officer'][:25]:<25}")
    print("=" * 85)
    print(f"Total Services: {len(records)}\n")


def search_by_keyword(records, keyword):
    """Search records by keyword across service name, category, and officer."""
    kw = keyword.strip().lower()
    results = [
        s for s in records
        if kw in s["service_name"].lower()
        or kw in s["category"].lower()
        or kw in s["designated_officer"].lower()
    ]
    return results


def count_per_category(records):
    """Count number of services per category."""
    counts = {}
    for s in records:
        cat = s["category"]
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def export_json(file_path="data/sample_records.json"):
    """Export the SERVICES list to a JSON file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(SERVICES, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Ensure JSON is exported
    export_json()

    print("\n--- S1: PRINT ALL REVENUE NOTIFIED SERVICES ---")
    print_all_services(SERVICES)

    print("--- S1: COUNT PER CATEGORY ---")
    cat_counts = count_per_category(SERVICES)
    for cat, count in sorted(cat_counts.items()):
        print(f"  • {cat:<22}: {count} services")
    print()

    print("--- S1: SEARCH BY KEYWORD ('farmer') ---")
    farmer_services = search_by_keyword(SERVICES, "farmer")
    for s in farmer_services:
        print(f"  [ID {s['id']}] {s['service_name']} (Time Limit: {s['time_limit_days']} days)")
    print()

    print("--- S1: SEARCH BY KEYWORD ('caste') ---")
    caste_services = search_by_keyword(SERVICES, "caste")
    for s in caste_services:
        print(f"  [ID {s['id']}] {s['service_name']} (Officer: {s['designated_officer']})")
    print()

