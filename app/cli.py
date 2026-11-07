"""
app/cli.py
Command Line Interface for AapleSeva Revenue Notified Services.
Uses app.records module to load, list, search, count, and display services.
"""

import sys
from pathlib import Path

# Add project root to path if running directly as a script
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.records import load_records, search, count_by, get_by_id


def format_service_row(record: dict) -> str:
    """Format a single record row for list displays."""
    s_id = str(record.get("id", ""))
    name = record.get("service_name", "")[:40]
    days = str(record.get("time_limit_days", ""))
    officer = record.get("designated_officer", "")[:26]
    return f"{s_id:<4} | {name:<40} | {days:<5} | {officer:<26}"


def display_services(records: list[dict]):
    """Print services in a formatted table."""
    if not records:
        print("\nNo services found.\n")
        return

    print("\n" + "=" * 82)
    print(f"{'ID':<4} | {'Service Name':<40} | {'Days':<5} | {'Designated Officer':<26}")
    print("-" * 82)
    for r in records:
        print(format_service_row(r))
    print("=" * 82)
    print(f"Total: {len(records)} service(s)\n")


def display_service_detail(record: dict):
    """Print complete details for a single service."""
    print("\n" + "=" * 65)
    print(f"SERVICE DETAILS: [ID {record.get('id')}] {record.get('service_name')}")
    print("=" * 65)
    print(f"Department               : {record.get('department')}")
    print(f"Category                 : {record.get('category')}")
    print(f"Statutory Time Limit     : {record.get('time_limit_days')} days")
    print(f"Designated Officer       : {record.get('designated_officer')}")
    print(f"First Appellate Officer  : {record.get('first_appellate_officer')}")
    print(f"Second Appellate Officer : {record.get('second_appellate_officer')}")
    print(f"Portal Source URL        : {record.get('source_url')}")
    print("=" * 65 + "\n")


def run_interactive():
    """Run interactive menu loop."""
    records = load_records()

    if not records:
        print("Error: Could not load any records from data source.")
        return

    while True:
        print("=" * 45)
        print("   AAPLESEVA NOTIFIED SERVICES CLI (S2)   ")
        print("=" * 45)
        print("  1. List All Notified Services (20)")
        print("  2. Search Services by Keyword")
        print("  3. View Counts by Category")
        print("  4. View Service Details by ID")
        print("  0. Exit")
        print("=" * 45)

        choice = input("Enter choice (0-4): ").strip()

        if choice == "1":
            display_services(records)

        elif choice == "2":
            kw = input("\nEnter search keyword (e.g. caste, farmer, land): ").strip()
            results = search(records, kw)
            print(f"\nSearch results for '{kw}':")
            display_services(results)

        elif choice == "3":
            field = input("\nEnter grouping field (press Enter for 'category'): ").strip()
            if not field:
                field = "category"
            counts = count_by(records, field)
            print(f"\nCounts grouped by '{field}':")
            print("-" * 45)
            for key, val in sorted(counts.items()):
                print(f"  • {key:<25}: {val} service(s)")
            print("-" * 45 + "\n")

        elif choice == "4":
            raw_id = input("\nEnter Service ID (1-20): ").strip()
            found = get_by_id(records, raw_id)
            if found:
                display_service_detail(found)
            else:
                print(f"\nService with ID '{raw_id}' was not found.\n")

        elif choice == "0":
            print("\nExiting AapleSeva CLI. Goodbye!\n")
            break

        else:
            print(f"\nInvalid option '{choice}'. Please choose 0 to 4.\n")


def main():
    """Main CLI entrypoint supporting both args and interactive mode."""
    records = load_records()

    # Simple command-line flag handling
    args = sys.argv[1:]
    if not args:
        run_interactive()
        return

    if "--list" in args:
        display_services(records)
    elif "--search" in args:
        idx = args.index("--search")
        if idx + 1 < len(args):
            kw = args[idx + 1]
            display_services(search(records, kw))
        else:
            print("Error: Missing search keyword. Usage: python app/cli.py --search <keyword>")
    elif "--id" in args:
        idx = args.index("--id")
        if idx + 1 < len(args):
            rec = get_by_id(records, args[idx + 1])
            if rec:
                display_service_detail(rec)
            else:
                print(f"Service ID {args[idx + 1]} not found.")
        else:
            print("Error: Missing service ID. Usage: python app/cli.py --id <id>")
    elif "--count" in args:
        field = "category"
        idx = args.index("--count")
        if idx + 1 < len(args) and not args[idx + 1].startswith("-"):
            field = args[idx + 1]
        counts = count_by(records, field)
        print(f"\nCounts by {field}:")
        for k, v in sorted(counts.items()):
            print(f"  • {k}: {v}")
    else:
        print("Usage:")
        print("  python app/cli.py                    # Interactive menu")
        print("  python app/cli.py --list             # List all services")
        print("  python app/cli.py --search <keyword> # Search services")
        print("  python app/cli.py --id <id>          # View details by ID")
        print("  python app/cli.py --count [field]    # Count grouped by field")


if __name__ == "__main__":
    main()

