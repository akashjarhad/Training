"""
app/smart_search.py
TF-IDF + cosine-similarity ranker for AapleSeva notified service records.

This powers the ``GET /search`` endpoint in ``app/main.py``. Unlike the plain
substring match in ``app.records.search``, it scores every record against the
query and returns the most relevant ones first, so "farmer land certificate"
still surfaces the Small and Marginal Farmer Certificate even though no single
record contains that whole phrase.

It depends on scikit-learn, so it is deliberately **not** imported by
``app/__init__.py``; the CLI and the unit tests stay on the standard library
and keep working without scikit-learn installed.

Usage
-----
    from app.smart_search import SmartSearch
    from app.records import load_records

    index = SmartSearch(load_records())
    for record, score in index.rank("caste certificate"):
        print(score, record["service_name"])
"""

from __future__ import annotations

from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Fields that carry searchable text. They are read with ``.get`` so a record is
# fine even when (like the 1058-row real dataset) some fields are absent or null.
SEARCH_FIELDS: tuple[str, ...] = (
    "service_name",
    "department",
    "sub_department",
    "category",
    "designated_officer",
    "first_appellate_officer",
    "second_appellate_officer",
)


def _record_text(record: dict) -> str:
    """Flatten the searchable fields of one record into a single string."""
    return " ".join(str(record.get(field, "") or "") for field in SEARCH_FIELDS)


class SmartSearch:
    """Rank AapleSeva records against a free-text query using TF-IDF + cosine.

    The TF-IDF matrix is fitted once, in ``__init__``, so repeated queries are
    just a cheap ``transform`` + ``cosine_similarity`` against the query vector.
    """

    def __init__(self, records: Iterable[dict]):
        self.records: list[dict] = list(records)
        self._texts: list[str] = [_record_text(r) for r in self.records]

        # Keep 1-character tokens (e.g. "7" in "7/12 Extract") so land-record
        # queries match. ``\w`` is Unicode-aware, so Marathi text in the real
        # dataset tokenises correctly too.
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            token_pattern=r"(?u)\b\w+\b",
            ngram_range=(1, 2),
        )

        if self._texts:
            self._matrix = self._vectorizer.fit_transform(self._texts)
        else:
            # Nothing to fit on; rank() will simply return an empty list.
            self._matrix = None

    def rank(
        self, query: str, top_k: int | None = None
    ) -> list[tuple[dict, float]]:
        """Return ``(record, score)`` pairs sorted by relevance, best first.

        Records that share no term with the query (score 0.0) are dropped, so
        the result only contains genuine matches. An empty query or an empty
        index yields an empty list.
        """
        if self._matrix is None or not query or not query.strip():
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).ravel()

        # (index, score) for non-zero matches, sorted by score then id for a
        # stable, deterministic tie-break.
        ranked = [
            (i, float(scores[i]))
            for i in range(len(self.records))
            if scores[i] > 0.0
        ]
        ranked.sort(key=lambda item: (-item[1], self.records[item[0]].get("id", 0)))

        results = [(self.records[i], score) for i, score in ranked]
        if top_k is not None:
            results = results[: max(0, top_k)]
        return results


def rank_records(
    records: list[dict], query: str, top_k: int | None = None
) -> list[tuple[dict, float]]:
    """Convenience wrapper: build a one-shot index and rank in a single call."""
    return SmartSearch(records).rank(query, top_k=top_k)
