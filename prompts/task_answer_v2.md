# Task: Answer a citizen question (v2 — check, then answer)

A citizen has asked a question about AapleSeva notified services. Before
answering, run a quick field check against the records below, then answer only
from what you confirmed is present.

CONTEXT RECORDS:
{context}

CITIZEN QUESTION:
{question}

Step 1 — CHECK (mentally; do not output it): for each piece of information the
question needs, mark it FOUND in the context or NOT FOUND. Remember that
`time_limit_days`, `designated_officer` and `first_appellate_officer` are
usually NOT published, so they will often be NOT FOUND. Anything about required
documents, fees, or application status is never in the data.

Step 2 — ANSWER: using only what you marked FOUND, reply with a single JSON
object and nothing else (do not include your check notes):
{"answer": "...", "confidence": "high|medium|low", "follow_up": "..."}
