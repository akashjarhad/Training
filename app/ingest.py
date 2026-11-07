"""
app/ingest.py
Cleans the raw Notified Services List PDF in data/raw/ into data/records.json.

Run app/fetch.py first to populate data/raw/.

    python -m app.ingest                 # parse everything (1058 services)
    python -m app.ingest --limit 20      # just a first slice
    python -m app.ingest --report        # parse, show diagnostics, write nothing


What the source actually contains
---------------------------------
NS_Service_List.pdf ("Notified Services List as of 31 March 2025") is a
36-page table exported from Excel with exactly five columns:

    अ.क्र                          serial number        -> Record.id
    विभाग                           department           -> Record.department
    उप विभाग                        sub-department       -> Record.sub_department
    सेवा                            service name         -> Record.service_name
    आपले सरकार पोर्टलवर उपलब्ध        on the portal?       -> Record.available_on_portal
                                    (होय = yes, नाही = no)

It publishes no time limit and no officer names, so Record.time_limit_days,
Record.designated_officer and Record.first_appellate_officer are left None.
Those values are not available anywhere public on aaplesarkar.mahaonline.gov.in
either, so they are reported as missing rather than invented.

Two further quirks of the source, both handled below:

1. Cells are merged and vertically centred, so one logical row spans several
   physical text lines and its serial number can sit on any one of them.
   Rows are reassembled by attaching each line to its nearest serial number.

2. The PDF mixes the Unicode font "Nirmala UI" with the legacy non-Unicode
   Marathi font "DVOT-SurekhMR". Text set in the legacy font extracts with
   mangled characters (नियम comes out as वनयम). That corruption is baked into
   the published file; correcting it would need OCR or a glyph remapping
   table. Affected rows are counted and reported, not silently dropped.


Known limitations
-----------------
Verified correct: the row count (1058, cross-checked against the one
holdfast/नाही cell per row found in the page geometry), the serial numbers
(contiguous 1..1058, no gaps or duplicates), and the department,
sub-department and portal columns (populated for all 1058 rows, with the
per-department totals summing exactly to 1058).

The one soft spot is the service description of a handful of very tall rows.
The serial number is drawn vertically centred in its merged cell, so for a
row whose description runs to twenty-odd lines the serial lands mid-cell and
the last line or two of the description falls after it -- and is then read as
the start of the next service. Serial 1018 is the clearest example. Fixing
this exactly needs the table's true row bands, which are present in the file
as per-cell clipping rectangles, but the text inside them is font-encoded
rather than Unicode, so using them would mean re-implementing pypdf's CMap
decoding and glyph-width spacing. That was judged not worth it for the number
of rows involved; the column values above are unaffected.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

from app.models import Record

SOURCE_FILENAME = "NS_Service_List.pdf"
SOURCE_URL = "https://aaplesarkar.mahaonline.gov.in/pdf/NS_Service_List.pdf"

# Column boundaries as character offsets into a layout-mode text line.
# pypdf's layout mode pads each line with spaces so columns line up as they do
# on the page. Measured across all 36 pages, segment start offsets cluster at
# 0, 12-29, 51-86 and 99-134, and cell text ends by offset 46 in the
# department column and 100 in the sub-department column, so these three
# boundaries sit in genuinely empty gutters.
SR_NO_COLUMN = (0, 10)
DEPARTMENT_COLUMN = (10, 48)
SUB_DEPARTMENT_COLUMN = (48, 98)
SERVICE_START = 98

YES_MARATHI = "होय"
NO_MARATHI = "नाही"

# The service column gets no fixed right-hand boundary. Service descriptions
# are centred and frequently render wider than their column: 727 of them
# cross offset 150, and the widest reaches 195, straight through where the
# last column sits. A fixed cut there silently truncated service names
# ("पोलीस" -> "पोली", "कररता ना-" -> "करर").
#
# Instead the last column is found by its own content. It only ever holds
# होय (yes) or नाही (no) and it is the rightmost column, so the token is
# matched at end of line and only beyond this offset -- the leftmost होय/नाही
# in the whole document starts at 158. Everything to its left is the service.
PORTAL_MIN_OFFSET = 155
_PORTAL_PATTERN = re.compile(f"({YES_MARATHI}|{NO_MARATHI})" + r"\s*$")

# The source publishes exactly this many notified services. The parse is
# checked against it so a layout change cannot quietly drop rows.
EXPECTED_SERVICE_COUNT = 1058

# The exact cell texts of the table header, which wraps over three lines:
#   'अ . क्र | विभाग | उप विभाग | सेिा | आपले सरकार'
#                                     | 'पोर्टलिर उपलब्ध'
# Spellings as the PDF's fonts actually extract them are included alongside
# the correct Unicode spellings.
_HEADER_CELL_TEXTS = {
    "अ . क्र",
    "अ.क्र",
    "विभाग",
    "उप विभाग",
    "सेिा",
    "सेवा",
    "आपले",
    "सरकार",
    "आपले सरकार",
    "पोर्टलिर",
    "पोर्टलवर",
    "उपलब्ध",
    "पोर्टलिर उपलब्ध",
    "पोर्टलवर उपलब्ध",
    "आपले सरकार पोर्टलिर उपलब्ध",
    "आपले सरकार पोर्टलवर उपलब्ध",
}

# Devanagari block; used to spot the legacy-font corruption signature.
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
# In correct Marathi an i-matra (ि) follows its consonant. The legacy font
# dump emits a bare "व" where the matra belongs, producing the telltale
# sequences below.
_MANGLED_HINTS = ("वनयम", "अविवनयम", "वनििय", "प्राविकरि", "विभागाकडे")


def get_raw_path(raw_dir=None) -> Path:
    """Return the path to the downloaded source PDF."""
    if raw_dir:
        return Path(raw_dir) / SOURCE_FILENAME
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "raw" / SOURCE_FILENAME


def get_output_path() -> Path:
    """Return the default output path, data/records.json."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "records.json"


def _split_portal(line: str) -> tuple[str, str]:
    """
    Peel the last column off a line.

    Returns (everything_left_of_it, portal_token). The token is only accepted
    at end of line and past PORTAL_MIN_OFFSET so that the words होय and नाही
    occurring inside a service description cannot be mistaken for it.
    """
    match = _PORTAL_PATTERN.search(line)
    if match and match.start() >= PORTAL_MIN_OFFSET:
        return line[: match.start()], match.group(1)
    return line, ""


def _slice_cells(line: str) -> dict:
    """Cut one layout-mode line into its five column cells."""
    body, portal = _split_portal(line)
    return {
        "sr_no": body[slice(*SR_NO_COLUMN)].strip(),
        "department": body[slice(*DEPARTMENT_COLUMN)].strip(),
        "sub_department": body[slice(*SUB_DEPARTMENT_COLUMN)].strip(),
        # No right-hand bound: the service description may legitimately run
        # past where the last column starts.
        "service_name": body[SERVICE_START:].strip(),
        "on_portal": portal,
    }


def _is_header(cells: dict) -> bool:
    """
    True for the table's own header line, which must not become a record.

    Matched against the header's exact strings. Substring matching is wrong
    here, because the header's vocabulary also occurs in real data: "उपलब्ध"
    (available) appears inside service names such as 'शोि उपलब्ध करणे', and
    "उप विभाग" appears inside real sub-department names such as
    'िहकार उप विभाग'. An earlier substring test silently deleted 10 services.

    The header wraps over three physical lines, and because the service column
    has no right-hand boundary its wrapped labels land in the service cell,
    so they are listed here too.
    """
    # The header carries no serial number, so anything numbered is a data row.
    if _parse_sr_no(cells["sr_no"]) is not None:
        return False

    if "क्र" in cells["sr_no"]:
        return True

    values = [
        " ".join(cells[name].split())
        for name in ("department", "sub_department", "service_name", "on_portal")
    ]
    filled = [v for v in values if v]
    return bool(filled) and all(v in _HEADER_CELL_TEXTS for v in filled)


def _parse_sr_no(cell: str):
    """Return the serial number in this cell, or None if it holds something else."""
    match = re.fullmatch(r"(\d{1,4})", cell.strip())
    return int(match.group(1)) if match else None


def extract_lines(pdf_path: Path) -> list[dict]:
    """
    Read the PDF and return one dict of column cells per physical text line.

    Each dict also carries its page number and the serial number if the line
    happens to hold one.
    """
    reader = PdfReader(str(pdf_path))
    lines = []

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except Exception as exc:
            # A single unreadable page should not lose the other 35.
            print(f"  warning: page {page_no} could not be read ({exc})",
                  file=sys.stderr)
            continue

        for line in text.splitlines():
            if not line.strip():
                continue
            cells = _slice_cells(line)
            if _is_header(cells):
                continue
            if not any(cells.values()):
                continue
            cells["page"] = page_no
            cells["sr_no_value"] = _parse_sr_no(cells["sr_no"])
            lines.append(cells)

    return lines


def group_rows(lines: list[dict]) -> list[dict]:
    """
    Reassemble physical lines into logical table rows.

    Cells in this table are merged and the exporter writes the serial number
    last, so a row that wraps over several lines always ends on the line
    carrying its serial number. One row is therefore every line following the
    previous serial number up to and including its own, which makes the
    segmentation exact rather than a guess.

    An earlier version attached each line to the *nearest* serial number
    instead. That silently mangled every row taller than two lines: for
    serial 6 the sub-department sat two lines above its own serial but only
    one below serial 5's, so it was filed under the wrong service, and
    serial 10 absorbed the first line of serial 11's description.
    """
    rows = []
    start = 0

    for idx, line in enumerate(lines):
        if line["sr_no_value"] is None:
            continue

        member_lines = lines[start : idx + 1]
        rows.append(
            {
                "sr_no": line["sr_no_value"],
                "page": line["page"],
                "department": _join([l["department"] for l in member_lines]),
                "sub_department": _join([l["sub_department"] for l in member_lines]),
                "service_name": _join([l["service_name"] for l in member_lines]),
                "on_portal": _join([l["on_portal"] for l in member_lines]),
            }
        )
        start = idx + 1

    # Anything after the final serial number is page furniture, not a row.
    trailing = [l for l in lines[start:] if any(
        l[c] for c in ("department", "sub_department", "service_name", "on_portal")
    )]
    if trailing:
        print(
            f"  warning: {len(trailing)} line(s) after the last serial number were "
            f"not part of any row",
            file=sys.stderr,
        )

    return rows


def _join(parts: list[str]) -> str:
    """Join the fragments of one cell that were split across physical lines."""
    return " ".join(p.strip() for p in parts if p and p.strip())


def _parse_on_portal(value: str):
    """Map the होय / नाही column onto a bool, or None if it says neither."""
    if not value:
        return None
    if YES_MARATHI in value:
        return True
    if NO_MARATHI in value:
        return False
    return None


def _looks_mangled(text: str) -> bool:
    """True if this text shows the legacy-font extraction corruption."""
    return any(hint in text for hint in _MANGLED_HINTS)


def build_records(rows: list[dict]) -> tuple[list[Record], list[dict]]:
    """
    Turn raw rows into validated Record objects.

    Every row is converted inside its own try/except: a row the source left
    broken is collected into `skipped` with the reason, so one bad row cannot
    abort the ingest and nothing fails silently.
    """
    records = []
    skipped = []

    for row in rows:
        try:
            record = Record(
                service_name=row["service_name"],
                department=row["department"],
                # Not published in this source. Left unset on purpose.
                time_limit_days=None,
                designated_officer=None,
                first_appellate_officer=None,
                source_url=SOURCE_URL,
                id=row["sr_no"],
                sub_department=row["sub_department"],
                available_on_portal=_parse_on_portal(row["on_portal"]),
            )
            records.append(record)

        except ValueError as exc:
            # Expected failure mode: a row with no usable service name.
            skipped.append(
                {
                    "sr_no": row.get("sr_no"),
                    "page": row.get("page"),
                    "reason": str(exc),
                    "raw": {k: v for k, v in row.items() if k != "page"},
                }
            )
        except Exception as exc:
            # Unexpected: keep going, but record the type so it can be chased.
            skipped.append(
                {
                    "sr_no": row.get("sr_no"),
                    "page": row.get("page"),
                    "reason": f"{type(exc).__name__}: {exc}",
                    "raw": {k: v for k, v in row.items() if k != "page"},
                }
            )

    return records, skipped


def diagnose(records: list[Record], skipped: list[dict]) -> dict:
    """Build a quality report for the parsed records."""
    ids = [r.id for r in records if r.id is not None]
    expected = set(range(1, max(ids) + 1)) if ids else set()
    missing_ids = sorted(expected - set(ids))
    duplicate_ids = sorted({i for i in ids if ids.count(i) > 1})

    coverage = {}
    for name in (
        "service_name",
        "department",
        "time_limit_days",
        "designated_officer",
        "first_appellate_officer",
        "source_url",
        "sub_department",
        "available_on_portal",
    ):
        filled = sum(
            1
            for r in records
            if getattr(r, name) is not None and getattr(r, name) != ""
        )
        coverage[name] = filled

    return {
        "records": len(records),
        "skipped": len(skipped),
        "expected": EXPECTED_SERVICE_COUNT,
        "matches_expected": len(records) == EXPECTED_SERVICE_COUNT,
        "serial_range": [min(ids), max(ids)] if ids else None,
        "contiguous": ids == sorted(ids) and missing_ids == [] and duplicate_ids == [],
        "missing_serial_numbers": missing_ids,
        "duplicate_serial_numbers": duplicate_ids,
        "field_coverage": coverage,
        "rows_with_font_corruption": sum(
            1 for r in records if _looks_mangled(r.service_name)
        ),
        "on_portal_yes": sum(1 for r in records if r.available_on_portal is True),
        "on_portal_no": sum(1 for r in records if r.available_on_portal is False),
        "departments": len({r.department for r in records if r.department}),
    }


def ingest(raw_dir=None, limit=None) -> tuple[list[Record], list[dict]]:
    """Read the raw PDF and return (records, skipped_rows)."""
    pdf_path = get_raw_path(raw_dir)
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"{pdf_path} not found. Run 'python -m app.fetch' first."
        )

    lines = extract_lines(pdf_path)
    rows = group_rows(lines)
    if limit is not None:
        rows = rows[:limit]
    return build_records(rows)


def save_records(records: list[Record], out_path=None) -> Path:
    """Write the records to JSON, keeping the Marathi text readable."""
    out_path = Path(out_path) if out_path else get_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.to_dict() for r in records]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Clean data/raw/NS_Service_List.pdf into data/records.json."
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="keep only the first N services",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="output path (default: data/records.json)",
    )
    parser.add_argument(
        "--raw-dir",
        metavar="PATH",
        help="directory holding the downloaded PDF (default: data/raw)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="print diagnostics without writing the output file",
    )
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be 1 or more")

    print("Ingesting AapleSeva notified services")
    try:
        records, skipped = ingest(raw_dir=args.raw_dir, limit=args.limit)
    except FileNotFoundError as exc:
        print(f"  error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"  error: could not parse the PDF ({type(exc).__name__}: {exc})",
              file=sys.stderr)
        return 1

    if not records:
        print("  error: no records parsed", file=sys.stderr)
        return 1

    report = diagnose(records, skipped)

    print(f"  parsed   {report['records']} services")
    print(f"  skipped  {report['skipped']} rows")
    print(f"  serials  {report['serial_range'][0]}..{report['serial_range'][1]}"
          f" (contiguous: {report['contiguous']})")
    if args.limit is None and not report["matches_expected"]:
        print(
            f"  WARNING: expected {report['expected']} services but parsed "
            f"{report['records']}. The source layout may have changed.",
            file=sys.stderr,
        )
    if report["missing_serial_numbers"]:
        preview = report["missing_serial_numbers"][:10]
        print(f"  gaps     {len(report['missing_serial_numbers'])} missing: {preview}")
    if report["duplicate_serial_numbers"]:
        print(f"  dupes    {report['duplicate_serial_numbers'][:10]}")
    print(f"  departments {report['departments']}")
    print(f"  on portal   yes={report['on_portal_yes']} no={report['on_portal_no']}")
    print()
    print("  field coverage (of %d records):" % report["records"])
    for name, filled in report["field_coverage"].items():
        note = ""
        if filled == 0:
            note = "  <- not published in this source"
        print(f"    {name:<26} {filled:>5}{note}")

    if report["rows_with_font_corruption"]:
        print()
        print(
            f"  note: {report['rows_with_font_corruption']} service names carry the "
            f"source PDF's legacy-font corruption"
        )

    for row in skipped[:5]:
        print(f"  skipped sr_no={row['sr_no']} page={row['page']}: {row['reason']}")

    if args.report:
        print()
        print("  --report given, no file written")
        return 0

    out_path = save_records(records, args.out)
    print()
    print(f"  wrote {len(records)} records -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
