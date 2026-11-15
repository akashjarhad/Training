"""
app/proforma.py
Parses the official English "List of Notified Services" proformas into records
that carry all six target fields.

Why this module exists
----------------------
``app/ingest.py`` parses NS_Service_List.pdf, the statewide notified services
list. That file has only five columns (serial number, department,
sub-department, service name, and whether the service is on the Aaple Sarkar
portal), so it leaves ``time_limit_days``, ``designated_officer`` and
``first_appellate_officer`` empty for every record.

Those three fields *are* published, just not in that file. Each department
issues its own notification under Section 3(1) of the Maharashtra Right to
Public Services Act, 2015, and those notifications tabulate exactly what is
missing:

    Sr. | Office/Department | Public Service Details | Time limit |
    Designated Officer | First Appellate Authority | Second Appellate Authority

This module reads those department proformas, so the project ends up with
records where all six fields are populated from a real published source.

A second benefit: these notifications are published in English with correctly
encoded text, so the records they produce are free of the legacy-font
corruption that affects the Marathi statewide list.

Usage
-----
    python -m app.proforma              # parse and print a summary
    python -m app.proforma --json       # dump the parsed records as JSON
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

from app.models import Record

# Proformas to parse. These are the per-department notifications that carry
# the time limit and officer columns; `app/fetch.py` downloads them by these
# same keys.
PROFORMAS = [
    {
        "key": "proforma_water",
        "filename": "RTS_Notified_Water_Supply.pdf",
        "department": "Water Supply and Sanitation Department",
        "url": (
            "https://cdnbbsr.s3waas.gov.in/s3347665597cbfaef834886adbb848011f/"
            "uploads/2025/01/20250125444972277.pdf"
        ),
    },
    {
        "key": "proforma_food",
        "filename": "RTS_Notified_Food_Civil_Supplies.pdf",
        "department": "Food, Civil Supplies and Consumer Protection Department",
        "url": (
            "https://cdnbbsr.s3waas.gov.in/s3e21e4e58ad9ab56e8a4634046da90113/"
            "uploads/2025/05/20250514954122339.pdf"
        ),
    },
]

# Header labels that mark where each column begins. Column boundaries are read
# off the document's own header row rather than hard-coded, because every
# department lays its proforma out slightly differently.
COLUMN_MARKERS = [
    ("sr_no", ("Sr.", "Sr ", "Sr")),
    ("office", ("Office/", "Office")),
    ("service_name", ("Public Service", "Public  Service")),
    ("time_limit", ("Time",)),
    ("designated_officer", ("Designated",)),
    ("first_appellate_officer", ("First",)),
    ("second_appellate_officer", ("Second",)),
]

# "15 days", "03 Working Days.", "180 Days after Proclamation", "30 ays" (sic)
_DAYS_PATTERN = re.compile(r"(\d{1,3})\s*(?:working\s+)?[dD]a?ys?", re.IGNORECASE)

# A service cell holds the service name followed by the documents the citizen
# must attach. The name is everything before that list starts.
_DOCS_PATTERN = re.compile(
    r"(?:\b\d\s*\.\s*)|(?:\bApplication\s+in\s+[Pp]rescribed\b)"
)

_SR_PATTERN = re.compile(r"^\s*(\d{1,3})\s*\.?\s*$")

# A table row opens with its serial number close to the left margin.
_ROW_START_PATTERN = re.compile(r"^\s{0,6}\d{1,3}\s*\.?\s")


def _is_furniture(line: str) -> bool:
    """True for page furniture that is not a table row."""
    stripped = line.strip()
    if not stripped:
        return True
    # The repeated column-number row: "(1) (2) (3) (4) (5) (6)"
    if re.fullmatch(r"[\(\)\d\s\.\|]+", stripped):
        return True
    low = stripped.lower()
    if "third and final appeal" in low or "appeal can be f" in low:
        return True
    if low.startswith("maharashtra right to public service"):
        return True
    if low.startswith("list of notified services"):
        return True
    return False


def get_raw_dir(raw_dir=None) -> Path:
    """Return the directory holding the downloaded proformas."""
    if raw_dir:
        return Path(raw_dir)
    return Path(__file__).resolve().parent.parent / "data" / "raw"


def _header_offsets(line: str) -> dict | None:
    """Read the offset of each column label off a header line."""
    offsets = {}
    for name, markers in COLUMN_MARKERS:
        for marker in markers:
            pos = line.find(marker)
            if pos != -1:
                offsets[name] = pos
                break
    required = ("service_name", "time_limit", "designated_officer")
    if all(k in offsets for k in required):
        offsets.setdefault("sr_no", 0)
        return offsets
    return None


def _snap_boundaries(
    offsets: dict, lines: list[str], look_left: int = 8, look_right: int = 5
) -> list[tuple[str, int, int | None]]:
    """
    Turn header label offsets into column slices, nudged onto clean cuts.

    The header labels identify which column is which, but the data below is
    not aligned to the label text, so slicing exactly on a label position
    chops characters off one column and prepends them to the next
    ("Executive S Engineer In e Charge of Water Works").

    So each boundary is moved to the position nearby that is blank on the
    greatest number of table lines, which is where the real column edge is.
    Pure whitespace-gutter detection was tried instead and was not usable:
    on these proformas at least one line always bridges two columns, which
    merged "Public Service" with "Time limit" and lost the distinction.
    """
    if not lines:
        return []

    width = max(len(line) for line in lines)
    # collisions[i] = how many lines have a non-space character at position i
    collisions = [0] * (width + 1)
    for line in lines:
        for i, ch in enumerate(line):
            if not ch.isspace():
                collisions[i] += 1

    ordered = sorted(offsets.items(), key=lambda kv: kv[1])
    starts: list[tuple[str, int]] = []

    for name, label_pos in ordered:
        if label_pos <= 0:
            starts.append((name, 0))
            continue
        low = max(1, label_pos - look_left)
        high = min(width, label_pos + look_right)
        best_pos, best_cost = label_pos, None
        for pos in range(low, high + 1):
            cost = collisions[pos]
            closer = abs(pos - label_pos) < abs(best_pos - label_pos)
            if best_cost is None or cost < best_cost or (cost == best_cost and closer):
                best_pos, best_cost = pos, cost
        starts.append((name, best_pos))

    # Keep the columns strictly increasing, then pair each with the next.
    starts.sort(key=lambda t: t[1])
    out: list[tuple[str, int, int | None]] = []
    for i, (name, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else None
        out.append((name, start, end))
    return out


def _slice(line: str, bounds: list[tuple[str, int, int | None]]) -> dict:
    """Cut a layout-mode line into cells using the calibrated boundaries."""
    cells = {}
    for name, start, end in bounds:
        chunk = line[start:end] if end is not None else line[start:]
        cells[name] = " ".join(chunk.split())
    return cells


def parse_days(text: str):
    """
    Pull a whole number of days out of a time-limit cell.

    Returns the first number stated, which for a conditional limit such as
    "30 Days if home visit is required otherwise 03 Working Days" is the
    headline figure. Returns None when the cell states no number.
    """
    if not text:
        return None
    match = _DAYS_PATTERN.search(text)
    if not match:
        return None
    try:
        value = int(match.group(1))
    except ValueError:
        return None
    return value if 0 <= value <= 365 else None


def clean_service_name(text: str) -> str:
    """
    Strip the attached-documents list off a service cell.

    The proforma packs the service name and the documents the citizen must
    supply into one cell, e.g.
    "New water connection 1.Application in prescribed format 2.Ownership
    documents". Only the name belongs in ``service_name``.
    """
    if not text:
        return ""
    match = _DOCS_PATTERN.search(text)
    name = text[: match.start()] if match else text
    name = " ".join(name.split()).strip(" .,;:-")
    return name


def parse_proforma(pdf_path: Path, department: str, source_url: str) -> tuple[list[Record], list[dict]]:
    """
    Parse one department proforma into Records.

    Each row is converted inside its own try/except so a malformed row is
    collected with its reason instead of killing the run.
    """
    reader = PdfReader(str(pdf_path))
    records: list[Record] = []
    skipped: list[dict] = []

    # Pass 1: pull out the table's lines and locate the header.
    table_lines: list[tuple[int, str]] = []
    offsets: dict | None = None
    seen_header = False
    in_body = False

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except Exception as exc:
            print(f"  warning: page {page_no} unreadable ({exc})", file=sys.stderr)
            continue

        for line in text.splitlines():
            if not line.strip():
                continue

            if offsets is None:
                found = _header_offsets(line)
                if found is not None:
                    offsets = found
                    seen_header = True
                    continue
                # Everything before the header is the covering note.
                continue

            if _is_furniture(line):
                continue

            # The header wraps over several lines ("No Departments", "limite
            # for", "Authority"...). Those span the full table width, so
            # letting them through would wipe out the whitespace gutters the
            # column detection depends on. The body starts at the first
            # serial-numbered line; skip everything up to it.
            if not in_body:
                if not _ROW_START_PATTERN.match(line):
                    continue
                in_body = True

            table_lines.append((page_no, line))

    if not seen_header or offsets is None:
        raise ValueError("could not find the table header in this proforma")
    if not table_lines:
        raise ValueError("found the header but no table rows")

    # Pass 2: calibrate the columns on the real table lines, then slice.
    bounds = _snap_boundaries(offsets, [line for _, line in table_lines])
    if not bounds:
        raise ValueError("could not map the header labels onto table columns")

    current: dict | None = None
    current_page = 0

    def flush(row, page):
        """Turn an accumulated row into a Record."""
        if row is None:
            return
        try:
            name = clean_service_name(row["service_name"])
            if not name:
                raise ValueError("no service name in row")
            records.append(
                Record(
                    service_name=name,
                    department=department,
                    time_limit_days=parse_days(row["time_limit"]),
                    designated_officer=row.get("designated_officer") or None,
                    first_appellate_officer=row.get("first_appellate_officer") or None,
                    source_url=source_url,
                    sub_department=row.get("office") or None,
                    second_appellate_officer=row.get("second_appellate_officer") or None,
                    source_page=page,
                    time_limit_text=" ".join(row["time_limit"].split()) or None,
                    # These notifications are published in English with
                    # correctly encoded text, so unlike the statewide Marathi
                    # list these records carry no glyph corruption.
                    text_quality="ok",
                )
            )
        except Exception as exc:
            skipped.append({"page": page, "reason": f"{type(exc).__name__}: {exc}", "raw": row})

    for page_no, line in table_lines:
        cells = _slice(line, bounds)

        sr = cells.get("sr_no", "")
        is_new_row = bool(_SR_PATTERN.match(sr))

        if is_new_row:
            flush(current, current_page)
            current = dict(cells)
            current_page = page_no
        elif current is not None:
            # Continuation line: append each cell onto the open row. The
            # serial column is skipped so a stray "." under a serial number
            # cannot corrupt the row.
            for key, value in cells.items():
                if not value or key == "sr_no":
                    continue
                current[key] = (current.get(key, "") + " " + value).strip()

    flush(current, current_page)
    return records, skipped


def parse_all(raw_dir=None) -> tuple[list[Record], list[dict]]:
    """Parse every proforma present in data/raw/."""
    raw = get_raw_dir(raw_dir)
    all_records: list[Record] = []
    all_skipped: list[dict] = []

    for spec in PROFORMAS:
        path = raw / spec["filename"]
        if not path.exists():
            print(
                f"  {spec['key']}: {spec['filename']} not in {raw}. "
                f"Run 'python -m app.fetch' first.",
                file=sys.stderr,
            )
            continue
        try:
            recs, skipped = parse_proforma(path, spec["department"], spec["url"])
        except Exception as exc:
            print(f"  {spec['key']}: FAILED {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        print(f"  {spec['key']:<18} {len(recs):>3} services  ({spec['department']})")
        all_records.extend(recs)
        all_skipped.extend(skipped)

    return all_records, all_skipped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse the English department notified-service proformas."
    )
    parser.add_argument("--json", action="store_true", help="print records as JSON")
    parser.add_argument("--raw-dir", metavar="PATH", help="directory holding the PDFs")
    args = parser.parse_args(argv)

    print("Parsing notified-service proformas")
    records, skipped = parse_all(args.raw_dir)

    if not records:
        print("  no records parsed", file=sys.stderr)
        return 1

    complete = [r for r in records if r.is_complete()]
    print()
    print(f"  total records     {len(records)}")
    print(f"  fully complete    {len(complete)}  (all six target fields populated)")
    print(f"  skipped rows      {len(skipped)}")
    with_days = [r for r in records if r.time_limit_days is not None]
    if with_days:
        print(
            f"  time limits       {min(r.time_limit_days for r in with_days)}"
            f"-{max(r.time_limit_days for r in with_days)} days"
        )

    if args.json:
        print(json.dumps([r.to_dict() for r in records], indent=2, ensure_ascii=False))
    else:
        print()
        for r in records[:5]:
            print(f"  - {r.service_name}")
            print(f"      {r.time_limit_days} days | {r.designated_officer}")
            print(f"      appeal -> {r.first_appellate_officer}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
