# sanjivani-sj-13-aapleseva

## AapleSeva Project Card

- **Product:** AapleSeva Citizen Services Assistant - An automated platform and CLI tool for Maharashtra Government's Aaple Sarkar citizen services portal.
- **User:** Citizens of Maharashtra, students applying for admissions and scholarships, job aspirants, and farmers.
- **Problem:** People face confusion regarding document requirements, eligibility rules, and processing time for government certificates (Income, Domicile, Caste, Non-Creamy Layer).
- **Data Source:** Official Aaple Sarkar Portal (https://aaplesarkar.mahaonline.gov.in) and Maharashtra Right to Public Services Act (RTS Act, 2015).

---

## Project Structure

```text
sanjivani-sj-13-aapleseva/
├── .gitignore               # Ignored files (.venv, __pycache__, data/raw binaries)
├── requirements.txt         # Project requirements
├── README.md                # Project card and documentation
├── day01_intro.py           # Day 01: Project card with variables & f-strings
├── day01_menu.py            # Day 01: While-loop menu with domain rule check
├── data/
│   ├── sample_records.py    # 20 Revenue notified services, hand-written list of dicts
│   ├── sample_records.json  # Exported JSON dataset
│   ├── records.json         # 1058 real services parsed out of the official PDF
│   └── raw/                 # Downloaded source documents (not tracked)
│       └── manifest.json    # URL, size and SHA-256 of every download (tracked)
├── app/
│   ├── __init__.py          # Package initializer
│   ├── records.py           # load_records, search, count_by, get_by_id
│   ├── models.py            # Record dataclass
│   ├── fetch.py             # Downloads the source documents into data/raw/
│   ├── ingest.py            # Cleans the raw PDF into data/records.json
│   └── cli.py               # Interactive CLI and flag-based interface
└── tests/
    └── test_records.py      # Unit tests for core record functions
```

---

## S1: 20 Revenue Department Notified Services
The 20 most frequently used services recorded under Maharashtra Right to Public Services Act (RTS 2015):
1. Age, Nationality and Domicile Certificate (15 days)
2. Income Certificate (15 days)
3. Caste Certificate (21 days)
4. Non-Creamy Layer Certificate (21 days)
5. Certified Copy of 7/12 Extract (1 day)
6. Certified Copy of 8A Extract (1 day)
7. Senior Citizen Certificate (8 days)
8. Solvency Certificate (21 days)
9. Small and Marginal Farmer Certificate (15 days)
10. Temporary Residence Certificate (7 days)
11. Agriculturist Certificate (15 days)
12. Character Certificate (15 days)
13. Economically Weaker Section (EWS) Certificate (15 days)
14. Legal Heir Certificate (21 days)
15. Minority Certificate (15 days)
16. Certified Copy of Mutation Entry (5 days)
17. Attestation of Affidavit (1 day)
18. Land Valuation Certificate (15 days)
19. Permission for Non-Agricultural Assessment (30 days)
20. Public Event and Loudspeaker Permission (5 days)

Each record captures: `id`, `service_name`, `department`, `category`, `time_limit_days`, `designated_officer`, `first_appellate_officer`, `second_appellate_officer`, and `source_url`.

---

## How to Run

### Setup Virtual Environment:
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate
```

### S1 Demo:
```bash
python data/sample_records.py
```

### S2 Interactive CLI:
```bash
python app/cli.py
```

### S2 Direct CLI Flags:
```bash
# List all 20 services
python app/cli.py --list

# Search by keyword
python app/cli.py --search caste
python app/cli.py --search farmer

# View service details by ID
python app/cli.py --id 4

# View counts grouped by category
python app/cli.py --count category
```

### Run Tests:
```bash
python tests/test_records.py
```

---

## Real data pipeline

The dataset above is hand-written. This pipeline instead downloads what the
Maharashtra government actually publishes and parses it.

```bash
python -m app.fetch       # download source documents -> data/raw/
python -m app.ingest      # parse the PDF           -> data/records.json
```

### `app/fetch.py` - download

Fetches five real documents from `aaplesarkar.mahaonline.gov.in`, writing each
to `data/raw/` plus a `manifest.json` recording the URL, HTTP status, byte
count and SHA-256 of each one.

| Key | File | Bytes |
|---|---|---|
| `ns_service_list` | `NS_Service_List.pdf` - Notified Services List, as of 31 Mar 2025 | 1,835,225 |
| `rts_act_page` | `RigthToServiceAct.html` - Act landing page | 79,996 |
| `act` | `RTS_Act_2015.pdf` - the Act itself | 268,783 |
| `rules` | `RTS_Rules_Gazette.pdf` - gazette rules | 174,904 |
| `faq_en` | `RTS_FAQ_English.pdf` - FAQs (English) | 8,084,096 |

Separate connect (10 s) and read (60 s) timeouts, 3 attempts with linear
backoff on timeout and connection errors, no retry on 4xx. Downloads are
written to a `.part` file and renamed only after the body is validated, so an
interrupted run cannot leave a truncated file looking complete. Content type
is checked by magic bytes, not the `Content-Type` header, because this server
returns no content type at all for its PDFs. Each document is fetched in its
own `try`/`except`, so one dead link does not stop the others.

```bash
python -m app.fetch --list              # show the catalogue
python -m app.fetch --only act rules    # fetch a subset
python -m app.fetch --force             # re-download everything
```

### `app/ingest.py` - clean

Parses the notified services table out of the 36-page PDF into
`Record` objects and writes `data/records.json`.

Current result: **1058 services, 0 rows skipped, serial numbers contiguous
1..1058** across 31 departments (540 available on the portal, 518 not).

```bash
python -m app.ingest --report     # diagnostics only, writes nothing
python -m app.ingest --limit 20   # just a first slice
```

### Which fields the source actually publishes

`Record` (in `app/models.py`) carries the project's six target fields. The
published source only supports three of them:

| Field | Source |
|---|---|
| `service_name` | the PDF's `सेवा` column |
| `department` | the PDF's `विभाग` column |
| `source_url` | the document the row came from |
| `time_limit_days` | **not published** - always `null` |
| `designated_officer` | **not published** - always `null` |
| `first_appellate_officer` | **not published** - always `null` |

`NS_Service_List.pdf` has exactly five columns: serial number, department,
sub-department, service name, and whether the service is available on the
Aaple Sarkar portal. It carries no time limits and no officer names, and
neither does anything else public on the portal. Those three fields are left
`null` rather than guessed, so a `null` in `records.json` always means "the
source does not say" and never "the parser failed". Use
`Record.missing_fields()` to see which are absent for a given record.

Three columns the source *does* publish are kept as extras: `id` (the serial
number, which also makes `records.json` work with `app.records.get_by_id`),
`sub_department`, and `available_on_portal`.

### Known limitations

- **The source PDF is Marathi only**, and its text is partly corrupt at the
  source: it mixes the Unicode font *Nirmala UI* with the legacy non-Unicode
  *DVOT-SurekhMR*, so text set in the latter extracts with wrong characters
  (`नियम` comes out as `वनयम`). 199 of the 1058 service names are affected.
  Fixing it would need OCR or a glyph remapping table. The ingest counts and
  reports these rather than hiding them.
- **A few very tall rows have an imperfect service description.** The serial
  number is drawn vertically centred in its merged cell, so where a
  description runs to twenty-odd lines the last line or two can be read as
  the start of the next service (serial 1018 is the clearest case). The
  department, sub-department, portal flag and serial numbers are unaffected.
