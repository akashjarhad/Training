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
├── .gitignore               # Ignored files (.venv, __pycache__, data/raw binaries, .env)
├── .env.example             # Tracked template for LLM API keys (.env itself is gitignored)
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
│   ├── smart_search.py      # TF-IDF + cosine ranker that powers /search
│   ├── llm.py               # Groq/Gemini provider wrapper that powers /chat
│   ├── main.py              # FastAPI service (/health, /records, /search, /questions, /chat)
│   └── cli.py               # Interactive CLI and flag-based interface
├── prompts/
│   ├── system.md            # AapleSeva assistant system prompt
│   ├── task_answer_v1.md    # Task prompt v1 (direct grounded answer)
│   └── task_answer_v2.md    # Task prompt v2 (check-then-answer)
├── analysis/
│   ├── __init__.py          # Package initializer
│   └── explore.py           # pandas facts about the record set
├── docs/
│   ├── how_llms_work.md     # How LLMs work (own words, 1 diagram)
│   └── questions.md         # 10 real AapleSeva citizen questions
├── eval/
│   └── prompt_compare.md    # Compares prompt v1 vs v2 on the 10 questions
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

# Install all dependencies (records core, fetch/ingest, FastAPI, search, analysis)
python -m pip install -r requirements.txt
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

## S3: FastAPI Service (`app/main.py`)

An HTTP API over the AapleSeva record set, with smart (TF-IDF + cosine) search.

### Run the server:
```bash
python -m uvicorn app.main:app --reload
# open http://127.0.0.1:8000/docs for the interactive Swagger UI
```

### Endpoints:
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check + number of loaded records |
| GET | `/records?limit=N` | List records, optionally capped with `limit` |
| GET | `/records/{id}` | Fetch one record; `404` when the id is unknown |
| GET | `/search?q=<query>&top_k=N` | TF-IDF + cosine ranking of records to `q` |
| POST | `/questions` | Submit a citizen question (stored in `data/questions.json`) |
| POST | `/chat` | Ask the AapleSeva LLM assistant; returns `answer`, `confidence`, `follow_up` |

### Examples:
```bash
# Liveness
curl "http://127.0.0.1:8000/health"

# First 5 records
curl "http://127.0.0.1:8000/records?limit=5"

# One record by id
curl "http://127.0.0.1:8000/records/4"

# Missing id -> 404
curl -i "http://127.0.0.1:8000/records/999"

# Smart search (ranks best matches first)
curl "http://127.0.0.1:8000/search?q=caste%20certificate&top_k=5"

# Submit a question
curl -X POST "http://127.0.0.1:8000/questions" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What documents are needed for an income certificate?\",\"name\":\"Riya\",\"service_id\":2}"
```

`/search` is powered by `app/smart_search.py`: it fits a TF-IDF vectoriser over each
record's searchable text (service name, department, category, officers) and ranks by
cosine similarity to the query, so multi-word queries still surface relevant records
even when no single record contains the whole phrase. An empty `q` returns all records
unranked, matching the CLI's substring search behaviour.

---

## S4: Data Analysis (`analysis/explore.py`)

Quick pandas exploration of the record set. Prints three labelled facts: dataset
scale (services / departments / categories), the most common category with the full
breakdown, and the statutory time-limit profile.

```bash
# Default dataset (data/sample_records.json)
python -m analysis.explore

# Point at the 1058-row real dataset instead
python -m analysis.explore --file data/records.json
```

---

## S5: LLM Chat Assistant (`POST /chat`)

`app/llm.py` wraps two providers — **Groq** and **Google Gemini** — both through
their OpenAI-compatible Chat Completions endpoint, so no provider SDK is needed.
`POST /chat` retrieves the most relevant records for the question (RAG via the
TF-IDF search), fills a task prompt from `prompts/`, calls the LLM, and returns
parsed JSON: `answer`, `confidence`, `follow_up`.

### Configure keys
```bash
cp .env.example .env      # then add a Groq or Gemini API key
# .env is gitignored and never committed; .env.example is the tracked template.
```

Run without keys (canned responses, for dev/demo):
```bash
# Windows PowerShell
$env:LLM_MOCK="1"; python -m uvicorn app.main:app --reload
```

### Use it
```bash
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" ^
  -d "{\"question\":\"Which department handles income certificates?\"}"
```

Response: `{"answer":"...","confidence":"high","follow_up":"...","provider":"groq","model":"...","prompt_version":"v1","retrieved":[2],...}`

Pick a provider or prompt version per call:
```json
{"question":"...", "provider":"gemini", "prompt_version":"v2", "top_k":5}
```

### Prompts (`prompts/`) and evaluation (`eval/`)
- `system.md` — the AapleSeva Mitra system prompt (persona + JSON output rules).
- `task_answer_v1.md` — direct grounded answer.
- `task_answer_v2.md` — check-then-answer (field check before answering).

See `eval/prompt_compare.md` for a comparison of v1 vs v2 across the 10 citizen
questions in `docs/questions.md`.

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

---

## Complete records: time limits and officers

The first version of this pipeline left `time_limit_days`,
`designated_officer` and `first_appellate_officer` `null` in every record,
because `NS_Service_List.pdf` — the statewide list of all 1058 notified
services — has only five columns and publishes none of them.

Those three fields *are* published, just in a different document. Every
department issues its own notification under Section 3(1) of the Act, and
those tabulate exactly what the statewide list omits:

```
Sr. | Office/Department | Public Service Details | Time limit |
Designated Officer | First Appellate Authority | Second Appellate Authority
```

`app/proforma.py` parses those notifications. `data/records.json` now holds:

| | records |
|---|---|
| statewide list (`NS_Service_List.pdf`) | 1058 |
| department proformas | 32 |
| **total** | **1090** |
| **of which complete — all six target fields** | **30** |

A complete record looks like this:

```json
{
  "service_name": "New water connection",
  "department": "Water Supply and Sanitation Department",
  "time_limit_days": 15,
  "designated_officer": "Executive Engineer In Charge of Water Works",
  "first_appellate_officer": "Superinutending engineer",
  "second_appellate_officer": "Chief Engineer",
  "time_limit_text": "15 days",
  "source_page": 2
}
```

Departments parsed so far: Water Supply and Sanitation (18 services), and
Food, Civil Supplies and Consumer Protection (14 services). Adding another
department is one entry in `PROFORMAS` in `app/proforma.py` plus one in
`DOCUMENTS` in `app/fetch.py` — the column boundaries are detected from each
document's own header, so no per-document tuning is needed.

### On the garbled Marathi

These notifications are published in **English with correctly encoded text**,
so all 30 complete records are free of the glyph corruption. That corruption
is specific to the statewide Marathi PDF, which mixes the Unicode font
*Nirmala UI* with the legacy non-Unicode *DVOT-SurekhMR*. Text set in the
latter extracts with wrong characters (`नियम` comes out as `वनयम`).

Every record now carries a `text_quality` field, so affected rows can be
filtered rather than silently trusted:

- `"ok"` — 891 records, text is reliable
- `"legacy_font_corrupt"` — 199 records, service name has mangled glyphs

```python
clean = [r for r in records if r["text_quality"] == "ok"]
```

Repairing the legacy font itself is not a text-level substitution: its
ToUnicode map collapses several distinct glyphs onto the same codepoint
(both the i-matra and `ध` arrive as `व`), so the original characters cannot be
recovered from the extracted string. It would need a font-specific glyph
table built from the raw CIDs. Flagging the rows and sourcing the complete
records from the English notifications addresses the same problem without
guessing at the text.

---

## S6: Semantic Search & RAG

### Semantic Search (`GET /search/semantic`)

Vector-based semantic search over document chunks using Chroma + sentence-transformers.

**Setup:**
```bash
# Index documents (one-time)
python -m app.embed --index

# Start the API server
python -m app.vectorstore
```

**API:**
```bash
# Search by meaning, not keywords
curl "http://127.0.0.1:8000/search/semantic?q=caste%20certificate%20time%20limit&top_k=5"
```

**Architecture:**
- **Chunking** (`app/chunking.py`): 1200 chars with 200 overlap, breaks at sentence boundaries
- **Embedding**: sentence-transformers/all-MiniLM-L6-v2 (384 dims, local, no API key)
- **Storage**: Persistent Chroma at `data/chroma/`
- **Supports**: PDF + HTML, preserves source/page/title metadata

See `SEMANTIC_SEARCH.md` for architecture details.

### RAG - Answer Questions with Citations (`POST /ask`)

Retrieves relevant chunks and uses an LLM to generate grounded answers with source citations.

**API:**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the time limit for a caste certificate?", "top_k": 5}'
```

**Response:**
```json
{
  "question": "What is the time limit for a caste certificate?",
  "answer": "The time limit is 21 days [RTS Notified Services, page 3]",
  "sources": [
    {"title": "RTS Notified Services", "page": 3, "distance": 0.32}
  ],
  "retrieved_count": 5,
  "provider": "groq",
  "model": "llama-3.3-70b-versatile"
}
```

**Key Features:**
- **Source citations**: Every answer cites [Document, page X]
- **Honest ignorance**: LLM says "I don't know" when context lacks answer
- **Configurable**: top-k, provider (groq/gemini), temperature

**Evaluation Framework:**

15-question test set with automatic scoring:
```bash
python -m eval.run_eval
```

Results compare multiple configs (chunk size, top-k) and update README with winner table.

See `RAG_SYSTEM.md` for implementation details.

## RAG Evaluation Results

| Config | Chunk Size | Overlap | Top-K | Avg Score | Notes |
|--------|------------|---------|-------|-----------|-------|
| larger-context | 1200 | 200 | 8 | 0.807 | 🏆 Winner |
| baseline | 1200 | 200 | 5 | 0.760 |  |

*Evaluated on 15 questions.*

**Key findings:**
- **top-k=8 outperforms top-k=5** (80.7% vs 76.0%) - more context helps answer complex questions
- **All 3 negative cases handled correctly** - LLM successfully said "I don't know" when documents lacked information (Q6, Q9, Q14)
- **Strong performance on time limits** (Q1, Q4, Q10) - 95%+ accuracy with proper citations
- **Officer identification excellent** (Q7) - retrieval correctly surfaced designated officer details

The larger-context config (top-k=8) is deployed as the default for `POST /ask`.

---

## Streamlit UI with Appeal Ladder

**Live Demo:** `streamlit run ui/app.py`

Interactive chat interface featuring:
- **Chat with AapleSeva**: Choose RAG (fast) or Agent (smart reasoning)
- **Source Citations**: Expandable source cards with relevance scores
- **Feedback**: Thumbs up/down saved to `ui/feedback.json`
- **Appeal Ladder** 🪜: Visual timeline calculator showing:
  - **Step 1**: Designated Officer (service delivery due date)
  - **Step 2**: First Appellate Authority (30 days to file, 30 days to decide)
  - **Step 3**: Second Appellate Authority (30 days to file, 30 days to decide)
  - **Step 4**: RTS Commission (final state-level authority)

Each step shows:
- Officer name and designation
- Date the step opens
- Filing deadline (for appeals)
- Status indicator (⚪ not yet open | 🟢 on time | 🟡 can appeal | 🔴 overdue)

![AapleSeva Chat UI](docs/screenshots/streamlit-app.png)
*Screenshot: Chat interface with appeal ladder for water connection service*

**Usage:**
```bash
# Terminal 1: Start FastAPI backend
cd Training
python -m uvicorn app.main:app --reload

# Terminal 2: Start Streamlit UI
streamlit run ui/app.py
# Opens at http://localhost:8501
```

**Appeal Ladder Example:**
- Application date: 2026-11-01
- Service: New water connection (15-day limit)
- Service due: 2026-11-16
- If not delivered → First appeal by 2026-12-16
- First decision due: 2026-12-16
- If unfavorable → Second appeal by 2027-01-15
- Second decision due: 2027-01-15
- Can approach RTS Commission: 2027-01-15 onwards

---
