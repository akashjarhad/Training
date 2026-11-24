# AapleSeva — Interview Prep

Everything you need for a 60-second pitch, the "hardest problem" story, and
answers to the 10 questions you're most likely to be asked.

---

## 1. The 60-second pitch

> AapleSeva is an AI assistant that helps citizens of Maharashtra use the
> Right to Service Act — the law that puts a legal time limit on government
> certificates like income, caste, domicile, and non-creamy-layer.
>
> Today a citizen makes three or four trips to the Tahsildar's office because
> they don't know which documents to bring, how long a service should take, or
> that they can formally appeal when it runs late. AapleSeva answers all three
> in seconds, grounded in **1,090 notified services** pulled from the official
> Aaple Sarkar portal.
>
> You ask in plain language — *"how long does a caste certificate take, and
> what do I need?"* — a retrieval pipeline finds the right clauses in the Act
> and the per-department notifications, an LLM answers **with citations**, and
> a tool I built computes the statutory due date and walks you up the
> **appeal ladder** — Designated Officer, First Appellate, Second Appellate,
> the RTS Commission — showing the exact date each step opens.
>
> It's a FastAPI backend, a Streamlit chat UI, a Chroma vector store, and an
> agent that can call the due-date tool. 46 tests, Dockerized, CI on GitHub
> Actions, deployed to Render.

(~170 words; aim for 60 seconds, slow and clear.)

---

## 2. The hardest problem (your interview story)

> This is the story you tell when they ask "tell me about the hardest
> technical problem you solved." Use the structure: **situation →
> complication → decision → result.**

### Situation
Maharashtra publishes its notified services in **two layers**:

1. A **statewide list** (`NS_Service_List.pdf`) — every one of the 1,058
   notified services, across 31 departments. Broad but shallow: it has only
   five columns and publishes **no time limits and no officer names**.
2. **Per-department proformas** — each department's own Section 3(1)
   notification, which tabulates exactly what the statewide list omits: the
   time limit, the Designated Officer, and both appellate authorities. Narrow
   but complete.

### Complication
The two layers don't agree on names. The same service is called
**"Age, Nationality and Domicile Certificate"** in one list and
**"Domicile certificate"** in another; one is English, one is Marathi; and
the lists are **re-notified over time**, so a service can appear in more than
one document with slightly different wording. So three things had to be
solved at once:

- **Name matching** across English and Marathi variants of the same service.
- **"Latest list wins"** — when the same service appears in both the
  statewide list (no time limit) and a department proforma (full details),
  the complete, more-specific record has to win, and the citizen has to see
  one answer, not two.
- **Working days vs calendar days** — some proformas say *"15 days"*, others
  say *"03 Working Days"*. A due date computed the wrong way is legally wrong,
  not just inaccurate.

There was also a data-quality wrinkle: the statewide PDF is Marathi-only and
its text is **partly corrupt at the source** — it mixes a Unicode font with a
legacy non-Unicode font, so some service names extract with the wrong
characters (`नियम` → `वनयम`).

### Decision
I split the problem and made each part explicit instead of trying to merge
the two sources into one "smart" guess:

- **Ingest (`app/ingest.py` + `app/proforma.py`)** parses both layers into the
  same `Record` shape and keeps them side by side — 1,058 from the statewide
  list plus 32 from the proformas, **1,090 total**, of which **30 are
  complete** (all six target fields). I never fabricate the three missing
  fields; a `null` always means *"the source does not say,"* never *"the parser
  failed."* Each row carries a `text_quality` flag so the 199 garbled Marathi
  rows can be filtered rather than silently trusted.
- **Matching ("latest list wins")** lives in `app/tools.py::_find_service`. It
  does a case-insensitive substring match against the service name and
  department, **but it tries the records that actually have a
  `time_limit_days` first.** So the complete proforma record for, say, a water
  connection is matched before the bare statewide entry. The more specific,
  more recent source wins — by construction, not by a timestamp I'd have to
  maintain.
- **Working vs calendar days** is a **parameter** on the `rts_due_date` tool,
  not a hidden assumption. By default it counts calendar days (the common
  case); with `count_working_days=True` it skips weekends and a built-in
  Maharashtra holiday list for 2026–27. The Act says both, so the tool has to
  say both.

### Result
A citizen question like *"my water connection is late, what now?"* resolves
to **one** record — the complete one — and the appeal ladder renders with the
correct due date and the right kind of days. The garbled Marathi rows are
flagged, not hidden, and the English proformas (which are clean) carry every
complete record. Adding a new department is one entry in a `PROFORMAS` list
plus one in the download catalogue — the column boundaries are read off each
document's own header, so there's no per-document tuning.

**One thing I'd still change:** real fuzzy matching (token overlap /
embeddings) instead of substring, because substring still misses true
synonyms. The "latest list wins" ordering is the part I'm proudest of — it
turns a messy two-source reality into a single, defensible answer.

---

## 3. Ten likely questions, with answers

### Q1 — What is AapleSeva, in one sentence?
An AI assistant that answers Maharashtra citizens' questions about Right to
Service certificates — time limits, required documents, and the appeal
process — grounded in the official notified-services documents, with
citations.

### Q2 — Why RAG instead of fine-tuning a model?
The truth changes. The Act is re-notified, departments publish new
proformas, time limits move. Fine-tuning bakes a snapshot into weights and
can't cite a source. RAG keeps the source documents as the ground truth, so
an update is "re-fetch, re-index" — and every answer points back to the
exact document and page it came from. For a legal-rights tool, *show your
source* is the whole product.

### Q3 — What was the hardest part? *(lead into the story above)*
Reconciling two layers of official data that don't agree on names, that are
re-notified over time, and that disagree on whether a time limit counts
working or calendar days. The fix was three explicit decisions: keep both
sources, let the complete record win on matching, and make working-vs-
calendar-days a parameter on the due-date tool. *(Then tell the story.)*

### Q4 — How does the retrieval actually work?
Two stages. `/search` is **TF-IDF + cosine** over each record's searchable
text (name, department, category, officers) — fast, no model, good for
keyword queries. `/ask` and `/search/semantic` use **Chroma with
sentence-transformers/all-MiniLM-L6-v2** over 1,200-char chunks (200 overlap,
sentence-broken) of the Act, Rules, FAQs, and service list — good for
meaning-based queries. The eval set (15 questions) picked **top-k = 8** over
top-k = 5 (80.7% vs 76.0%), so 8 is the deployed default.

### Q5 — How do you stop the model from hallucinating?
Three ways. (1) The prompt instructs it to say **"I don't know"** when the
retrieved context lacks the answer — and eval Q6/Q9/Q14 (questions the data
can't answer) are required to fail in exactly that way. (2) Every answer must
carry a citation `[Document, page X]`; an answer with no citation is treated
as suspicious. (3) A 500-character input limit and a system-prompt isolation
boundary so injected instructions can't override the grounded-answer
behavior — there's a 16-test security suite for prompt injection.

### Q6 — Walk me through the appeal-ladder feature.
It's the signature UI feature. Pick a service and an application date; the
ladder renders four steps with the date each opens: **Designated Officer**
(service due date = application date + the service's time limit), **First
Appellate** (30 days to file once it's late), **Second Appellate**, then the
**RTS Commission**. Each step shows the officer name and a status dot — not
yet open, on time, can appeal, or overdue. The due date itself comes from the
`rts_due_date` agent tool, so the UI and the agent agree.

### Q7 — How did you evaluate quality?
A 15-question eval set (`eval/eval_set.json`) with an automatic scorer
(`eval/run_eval.py`). I compared two configs — chunk size and top-k — and put
the winner table in the README. Top-k = 8 won. The set deliberately includes
three *unanswerable* questions so "I don't know" is measured, not just
accuracy on answerable ones.

### Q8 — How is it production-ready?
Logging + metrics on every `/ask` request (latency, cached?, token estimates)
to `data/metrics.json` and a `/metrics` endpoint; an in-memory **cache**
(TTL 1h, ~40–60% hit rate, sub-50 ms on a hit vs ~1 s uncached); a 500-char
input limit; prompt-injection tests; Docker + docker-compose for API and UI;
GitHub Actions CI (ruff, pytest, docker build) with a green badge; and a
Render deployment with a public `/health`.

### Q9 — Why Groq and Gemini specifically?
Both expose an OpenAI-compatible Chat Completions endpoint, so one thin
client in `app/llm.py` talks to either — no per-provider SDK. Groq (Llama
3.3 70B) for speed and low cost, Gemini as a fallback. There's also a mock
mode (`LLM_MOCK=1`) so the whole app — and the tests — run with **no API
key**, which is what made the 46-test CI possible without secrets.

### Q10 — What would you do next?
Three things, in order. (1) **Real fuzzy matching** — token overlap or small
embeddings for service-name matching, so true synonyms hit instead of just
substrings. (2) **More department proformas** — the architecture is built for
it (one list entry per department), and each one lifts the count of
complete, six-field records. (3) **Marathi OCR / glyph remapping** to recover
the 199 garbled rows in the statewide list, or simply keep sourcing complete
records from the English proformas where the text is clean.

---

## Demo runbook (rehearse this twice before the interview)

1. **Backend up:** `python -m uvicorn app.main:app --reload` (or
   `LLM_MOCK=1` if no keys) → http://localhost:8000/docs
2. **UI up:** `streamlit run ui/app.py` → http://localhost:8501
3. **The three beats:**
   - *Ask:* "What is the time limit for a caste certificate?" → answer +
     citation.
   - *The hard one (must say "I don't know"):* a question the data can't
     answer (e.g. "What is the fee for a domicile certificate?") → graceful
     "I don't know."
   - *Appeal ladder:* pick "New water connection", application date today →
     ladder renders with the four steps and the dates.
4. **Show the receipts:** `/metrics`, `/health`, the eval winner table in
   README, `ruff check .` and `pytest` green.

> Rehearse it **twice** — once for timing (hit 60 seconds on the pitch), once
> for the "I don't know" beat (the most important moment: it proves the
> system won't invent answers).
