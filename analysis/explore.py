"""
analysis/explore.py
Print a few facts about the AapleSeva notified services dataset using pandas.

Run it from the project root::

    python -m analysis.explore
    python -m analysis.explore --file data/records.json

It loads the same JSON the rest of the project uses (via ``app.records``) into
a pandas ``DataFrame`` and prints three labelled facts about the record set.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.records import load_records


def to_dataframe(records: list[dict]) -> pd.DataFrame:
    """Build a DataFrame from the record list, keeping missing fields as NaN."""
    return pd.DataFrame(records)


def print_facts(df: pd.DataFrame) -> None:
    """Print three facts derived from the record DataFrame."""
    total = len(df)
    departments = df["department"].dropna().nunique() if "department" in df else 0
    categories = df["category"].dropna().nunique() if "category" in df else 0

    print("=" * 70)
    print("AapleSeva records - quick facts")
    print("=" * 70)

    # --- Fact 1: scale of the dataset -------------------------------------- #
    print(
        f"\n1. The dataset holds {total} notified service(s) across "
        f"{departments} department(s) and {categories} category/categories."
    )

    # --- Fact 2: most common category ------------------------------------- #
    if "category" in df and df["category"].notna().any():
        counts = df["category"].value_counts()
        top_cat = counts.idxmax()
        top_n = int(counts.max())
        print(
            f"2. The most common category is '{top_cat}' with {top_n} "
            f"service(s); the full breakdown is:"
        )
        for cat, n in counts.items():
            print(f"     - {cat}: {n}")
    else:
        # Fall back to department when no category column exists (real dataset).
        counts = df["department"].value_counts()
        top_dept = counts.idxmax()
        top_n = int(counts.max())
        print(
            f"2. The source has no 'category' column, so by department the "
            f"largest is '{top_dept}' with {top_n} service(s)."
        )

    # --- Fact 3: statutory time-limit profile ---------------------------- #
    if "time_limit_days" in df and df["time_limit_days"].notna().any():
        days = df["time_limit_days"].dropna()
        fastest = int(days.min())
        slowest = int(days.max())
        mean_days = days.mean()
        # Locate the slowest service name for a concrete reference point.
        slowest_idx = df["time_limit_days"].idxmax()
        slowest_name = df.loc[slowest_idx, "service_name"]
        print(
            f"3. Statutory time limits range from {fastest} to {slowest} day(s), "
            f"averaging {mean_days:.1f} day(s); the longest is "
            f"'{slowest_name}' at {slowest} day(s)."
        )
    else:
        print(
            "3. No 'time_limit_days' values are present - the published source "
            "does not carry statutory time limits, so this fact cannot be "
            "computed from the data."
        )

    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to a records JSON file (defaults to data/sample_records.json).",
    )
    args = parser.parse_args()

    records = load_records(args.file)
    if not records:
        print("No records loaded - check the data file path.")
        return

    df = to_dataframe(records)
    print_facts(df)


if __name__ == "__main__":
    main()
