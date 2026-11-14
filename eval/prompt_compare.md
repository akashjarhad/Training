# Prompt Comparison: v1 vs v2 on the 10 AapleSeva Questions

This evaluates the two task prompts in `prompts/` — `task_answer_v1.md`
(direct grounded answer) and `task_answer_v2.md` (check-then-answer) — across
the ten citizen questions in `docs/questions.md`.

## The two versions

- **v1 — Direct grounded.** Given the retrieved records and the question,
  answer using only the records; if a needed field is absent, say the data
  does not say.
- **v2 — Check-then-answer.** First run a mental field-by-field check, marking
  each needed piece of information FOUND or NOT FOUND (especially the three
  usually-unpublished fields), then answer only from what was FOUND.

The system prompt (`prompts/system.md`) is shared by both. The only difference
is the task prompt, selectable per call with `prompt_version` on `POST /chat`.

## Why these two

The AapleSeva dataset can answer three of the six target fields
(`service_name`, `department`, `source_url`) and cannot answer the other three
(`time_limit_days`, `designated_officer`, `first_appellate_officer`), plus
anything outside the schema (documents, fees, status). The interesting axis is
therefore **honest refusal on unanswerable questions**. v2's explicit field
check is designed to reduce gap-filling; v1 is simpler but more exposed to
hallucination.

## Rubric (per question)

- **A. Correctness** (answerable): the answer matches the data ground truth.
- **B. Honest refusal** (unanswerable): it says the data does not say, rather
  than inventing.
- **C. Confidence calibration**: high only when grounded; low when absent.
- **D. Follow-up quality**: a useful, specific next question.

## Per-question comparison

Ground truth is taken from `docs/questions.md`. The "Expected" columns are
**predictions** from the prompt design and the known data coverage; the
"Actual" columns are to be filled by running each prompt through `/chat`
(see *Run it for real* below).

| # | Question (short) | Data answers? | Ground truth | Expected v1 | Expected v2 | Predicted winner |
|---|---|---|---|---|---|---|
| Q1 | Caste certificate service name | Yes | "Caste Certificate" (id 3) | Names it, high | Names it, high | tie |
| Q2 | Department for income certificate | Yes | Revenue Department | Revenue Dept, high | Revenue Dept, high | tie |
| Q3 | Official portal | Yes | source_url | Gives URL, high | Gives URL, high | tie |
| Q4 | Time limit for income certificate | No | `time_limit_days` null | Says "data does not say" but may slip a number, low | Checks time_limit NOT FOUND -> refuses, low | **v2** |
| Q5 | Designated officer | No | `designated_officer` null | May invent an officer; should refuse | Checks officer NOT FOUND -> refuses, low | **v2** |
| Q6 | First appellate officer | No | `first_appellate_officer` null | May invent; should refuse | Checks NOT FOUND -> refuses, low | **v2** |
| Q7 | Certified copy of 7/12 extract | Yes | "Certified Copy of 7/12 Extract" (id 5) | Names it, high | Names it, high | tie |
| Q8 | Senior citizen certificate + category | Yes | id 7, Social Welfare | Answers, high | Answers, high | tie |
| Q9 | Required documents | No | no field | May invent a document list | No field found -> refuses, low | **v2** |
| Q10 | Track application status | No | no field | May give generic advice | No field found -> refuses, low | **v2** |

## Aggregate prediction

- **On answerable questions (Q1, Q2, Q3, Q7, Q8)** the two versions are
  expected to tie — both are grounded in the same retrieved records.
- **On unanswerable questions (Q4, Q5, Q6, Q9, Q10)** v2 is expected to refuse
  more reliably and calibrate confidence lower, because its field check
  surfaces the missing fields before answering. v1's risk is gap-filling:
  inventing an officer, a number of days, or a document list.
- **Cost:** v2 asks the model for an extra reasoning step, so it is slightly
  more verbose and a little slower per call. v1 is leaner.

Net: prefer **v2** when honesty on out-of-scope questions matters (the common
case for a government-services assistant); v1 is fine when latency and token
cost dominate and the questions are mostly within the data.

## Run it for real

The table above is a design-level prediction. To fill the "Actual" columns,
run each version on all ten questions through the API. This requires a provider
key in `.env` (or `LLM_MOCK=1` for canned responses — but note mock returns
identical text for both versions, so it only checks plumbing, not the
comparison):

```bash
# v1
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" \
  -d '{"question":"Which department handles income certificates?","prompt_version":"v1"}'

# v2 (same question, other prompt)
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" \
  -d '{"question":"Which department handles income certificates?","prompt_version":"v2"}'
```

Each response returns `answer`, `confidence`, `follow_up` (plus `provider`,
`model`, `prompt_version`, `retrieved`). Repeat for the ten questions in
`docs/questions.md`, record `answer`/`confidence`/`follow_up`, and score with
the rubric above to turn these predictions into measured results.
