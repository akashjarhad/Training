# Task: Answer a citizen question (v1 — direct grounded)

A citizen has asked a question about AapleSeva notified services. The records
below are the most relevant ones retrieved for this question. Answer using only
these records.

CONTEXT RECORDS:
{context}

CITIZEN QUESTION:
{question}

Reply with a single JSON object and nothing else:
{"answer": "...", "confidence": "high|medium|low", "follow_up": "..."}

- If the records contain the answer, state it plainly and set a matching
  confidence.
- If the records do not contain a needed field (often `time_limit_days`,
  `designated_officer`, `first_appellate_officer`), say the published data does
  not say and set confidence to "low".
