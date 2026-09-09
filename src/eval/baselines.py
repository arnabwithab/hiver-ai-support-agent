"""F008: trivial and simple baselines. Design §10. Stdlib only — no LLM, no keys.

Two baselines, both buildable offline and scorable by metrics.evaluate():
  * MajorityBaseline  F008-1  predict() = train majority intent; draft() =
                            canned fixed reply string.
  * TfidfBaseline     F008-2  hand-rolled TF-IDF (word counts + idf by hand)
                            over train texts; draft() returns the top-1
                            most-similar train reply. predict() maps a text to
                            the train intent of its nearest reply.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from src.utils.logger import logger

_WORD = re.compile(r"[a-z0-9']+")
_CANNED = (
    "Thanks for reaching out. We're looking into this and will follow up "
    "with a solution shortly."
)


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


class MajorityBaseline:
    """F008-1: always predict the training majority intent; fixed canned reply."""

    def __init__(self):
        self.majority = None

    def fit(self, labels) -> "MajorityBaseline":
        if labels:
            counts = Counter(labels)
            self.majority = sorted(counts, key=lambda label: (-counts[label], str(label)))[0]
        logger.info("majority baseline fitted; majority=%s", self.majority)
        return self

    def predict(self, text) -> object:
        return self.majority

    def draft(self, text) -> str:
        return _CANNED


class TfidfBaseline:
    """F008-2: stdlib TF-IDF retrieval over train replies.

    Terms are weighted as tf * idf with idf = log(1 + N/df). draft() returns
    the train reply with max cosine similarity to the query; predict() returns
    the intent tied to that nearest reply.
    """

    def __init__(self):
        self._docs: list[tuple[str, object, Counter, float]] = []  # (text, intent, tf, norm)
        self._idf: dict[str, float] = {}

    def fit(self, texts, intents=None) -> "TfidfBaseline":
        if intents is None:
            intents = [None] * len(texts)
        n = len(texts)
        df = Counter()
        for text in texts:
            for term in set(_tokens(text)):
                df[term] += 1
        self._idf = {term: math.log(1 + n / count) for term, count in df.items()}
        self._docs = []
        for text, intent in zip(texts, intents):
            tf = Counter(_tokens(text))
            norm = math.sqrt(sum((c * self._idf.get(t, 0.0)) ** 2 for t, c in tf.items()))
            self._docs.append((text, intent, tf, norm))
        logger.info("tfidf baseline fitted over %d docs", n)
        return self

    def _score(self, query: Counter) -> list[float]:
        q_norm = math.sqrt(sum((c * self._idf.get(t, 0.0)) ** 2 for t, c in query.items()))
        out = []
        for _, _, tf, d_norm in self._docs:
            if q_norm == 0 or d_norm == 0:
                out.append(0.0)
                continue
            dot = sum(tf[t] * c * self._idf.get(t, 0.0) ** 2 for t, c in query.items())
            out.append(dot / (q_norm * d_norm))
        return out

    def draft(self, text) -> str | None:
        return self._nearest(text)[0]

    def predict(self, text) -> object:
        return self._nearest(text)[1]

    def _nearest(self, text) -> tuple[str | None, object]:
        if not self._docs:
            return (None, None)
        q = Counter(_tokens(text))
        scores = self._score(q)
        idx = max(range(len(scores)), key=scores.__getitem__)
        return (self._docs[idx][0], self._docs[idx][1])
