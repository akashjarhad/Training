# PROGRESS — AapleSeva

Build tracker for `sanjivani-sj-13-aapleseva`. Every deliverable below is
**closed** ✅. The final tag is `final`.

> Rehearse the live demo twice before the interview — see the runbook in
> `docs/interview.md`. (That step is the presenter's, not the repo's.)

---

## Day 01 — Repo, card, menu
- [x] Public repo `sanjivani-sj-13-aapleseva` cloned
- [x] `README.md` project card (product, user, problem, data source)
- [x] `day01_intro.py` — card with variables + f-strings, asks name/question via `input()`
- [x] `day01_menu.py` — while-loop menu (about / sample questions / one if-elif rule check / exit)
- [x] Pushed

## Week 1 — Records, real data, FastAPI, analysis, docs
- [x] S1: 20 Revenue services in `data/sample_records.py` + `.json` (print all, search by keyword, count per category)
- [x] S2: `app/records.py` (load_records, search, count_by, get_by_id) + `app/cli.py`; `.venv`, `requirements.txt`, `.gitignore`
- [x] S1: download real slice into `data/raw/`; `app/ingest.py` cleans → `data/records.json` with try/except
- [x] S2: `Record` dataclass in `app/models.py`; `app/fetch.py` downloads 3+ docs (timeouts, error handling)
- [x] S1: `app/main.py` FastAPI — `/health`, `/records?limit=`, `/records/{id}` (404), `/search?q=`, `POST /questions`; README "How to run"
- [x] S2: `analysis/explore.py` (3 pandas facts); `app/smart_search.py` TF-IDF + cosine powers `/search`
- [x] Tag `week-1`
- [x] `docs/how_llms_work.md` (own words, 1 diagram)
- [x] 10 real AapleSeva questions (`docs/questions.md`); Q6 one the data can't answer
- [x] Checkpoint 1: FastAPI runs, `/docs` shown, one function explained
- [x] Tag `checkpoint-1`

## LLM chat + prompts
- [x] S1: `app/llm.py` Groq/Gemini wrapper + `POST /chat` with AapleSeva system prompt; `.env` not committed, `.env.example` committed
- [x] S2: `prompts/` (system + 2 task prompts); `/chat` returns JSON (answer, confidence, follow_up); `eval/prompt_compare.md` compares 2 versions on the 10 questions

## Semantic search + RAG
- [x] S1: `app/chunking.py` + `app/embed.py` (source/page/title kept); semantic search for the 10 questions; `eval/search_results.md`
- [x] S2: `app/vectorstore.py` — persistent Chroma collection; `GET /search/semantic?q=`
- [x] S1: `app/rag.py` + `POST /ask` with citations; says "I don't know" for Q6
- [x] S2: `eval/eval_set.json` (15 rows) + `eval/run_eval.py`; 2 configs (chunk size / top-k); winner table in README (top-k=8, 80.7%)

## Agent + Streamlit UI
- [x] S1: `app/tools.py` `rts_due_date` (records.json lookup + datetime; calendar or working days excl. weekends/holidays); `app/agent_loop.py` hand-written agent (RAG search + tool)
- [x] S2: `app/graph.py` LangGraph rebuild (memory + one approval step); `POST /agent`
- [x] `ui/app.py` Streamlit chat → `/ask` or `/agent`, shows citations, thumbs up/down; **appeal ladder** (Designated → First → Second → RTS Commission with dates); screenshot in README
- [x] Checkpoint 2 live demo
- [x] Tag `checkpoint-2`

## Tests, Docker, CI, deploy, production, sell
- [x] S1: `tests/` 8+ pytest (records, search, /health, /ask with fake LLM, agent tool); `ruff check .` passes
- [x] S2: `Dockerfile` + `.dockerignore` + `docker-compose.yml` (API + UI up with one command); README "Run with Docker"
- [x] S1: `.github/workflows/ci.yml` (ruff, pytest, docker build); green badge in README; 1 PR from a feature branch merged after CI green
- [x] S2: deploy to Render; `/health` public; live URL in README
- [x] S1: log latency + tokens per request, simple cache, input limits, one prompt-injection test; README "Production notes" with numbers
- [x] S2: README sells (problem, Mermaid architecture, demo video link, results table); `docs/resume.md` (3 resume bullets)

## Final
- [x] `docs/interview.md` — 60-second pitch + 10 Q&A + hardest-problem story
- [x] Close every open item in `PROGRESS.md`
- [ ] **Rehearse the demo twice** *(presenter step — see `docs/interview.md` runbook)*
- [x] Tag `final`

---

## Demo verification (run by the build)

- API: `GET /health` returns 200 with record count.
- `GET /records?limit=2` returns two records.
- `GET /search?q=caste` returns ranked matches.
- `POST /ask` returns a cited answer (mock LLM, no keys needed).
- The unanswerable question returns "I don't know."
- `ruff check .` clean; `pytest` green; `docker compose up` starts API + UI.
