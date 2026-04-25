"""TF-IDF cosine similarity matcher.

Pure-stdlib implementation — no scikit-learn or numpy dependency. The math
is small enough that handwritten Python is plenty fast for the document
sizes this tool sees (a few hundred contract reqs × a few hundred procedure
clauses tops).

TF-IDF gives more weight to tokens that are rare across the corpus, which
is the right behaviour for spec / procedure matching: shared boilerplate
("requirement", "system", "shall") gets discounted, distinctive domain
terms ("autopilot", "torque", "soffite") drive the score.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Sequence, Set

from ..models import DDERow, Match


_TOKEN = re.compile(r"[A-Za-z][A-Za-z\-]+")
_STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "from", "by", "as", "at", "be", "is", "are", "was", "were", "been",
    "shall", "must", "should", "may", "can", "will", "not",
    "this", "that", "these", "those", "it", "its", "their",
}


def _tokenise(text: str | None) -> List[str]:
    if not text:
        return []
    return [
        t.lower()
        for t in _TOKEN.findall(text)
        if len(t) >= 3 and t.lower() not in _STOPWORDS
    ]


def _tf(tokens: Sequence[str]) -> Dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    n = len(tokens)
    return {term: count / n for term, count in counts.items()}


def _idf(corpus: Sequence[Sequence[str]]) -> Dict[str, float]:
    """Smoothed IDF: log((N + 1) / (df + 1)) + 1."""

    n_docs = len(corpus)
    df: Counter = Counter()
    for tokens in corpus:
        for term in set(tokens):
            df[term] += 1
    return {
        term: math.log((n_docs + 1) / (count + 1)) + 1.0
        for term, count in df.items()
    }


def _vector(tokens: Sequence[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf = _tf(tokens)
    return {term: weight * idf.get(term, 0.0) for term, weight in tf.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    # iterate over the smaller dict for the dot product
    if len(a) > len(b):
        a, b = b, a
    dot = sum(weight * b.get(term, 0.0) for term, weight in a.items())
    if dot == 0.0:
        return 0.0
    norm_a = math.sqrt(sum(w * w for w in a.values()))
    norm_b = math.sqrt(sum(w * w for w in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def run(
    contract_rows: List[DDERow],
    procedure_rows: List[DDERow],
    threshold: float = 0.20,
) -> List[Match]:
    """Return one ``Match`` per (req, clause) with cosine ≥ threshold."""

    contract_tokens = [_tokenise(r.text) for r in contract_rows]
    procedure_tokens = [_tokenise(c.text) for c in procedure_rows]

    # IDF computed across the union corpus so both sides share term weights.
    idf = _idf(contract_tokens + procedure_tokens)

    contract_vecs = [_vector(t, idf) for t in contract_tokens]
    procedure_vecs = [_vector(t, idf) for t in procedure_tokens]

    matches: List[Match] = []
    for req, req_vec in zip(contract_rows, contract_vecs):
        if not req_vec:
            continue
        for clause, clause_vec in zip(procedure_rows, procedure_vecs):
            if not clause_vec:
                continue
            score = _cosine(req_vec, clause_vec)
            if score < threshold:
                continue
            top_terms = sorted(
                (term for term in req_vec if term in clause_vec),
                key=lambda term: -(req_vec[term] * clause_vec.get(term, 0.0)),
            )[:5]
            matches.append(
                Match(
                    contract_id=req.stable_id,
                    procedure_id=clause.stable_id,
                    matcher="similarity",
                    score=score,
                    evidence="tf-idf top terms: " + ", ".join(top_terms),
                )
            )
    return matches
