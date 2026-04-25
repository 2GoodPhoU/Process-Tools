"""Keyword-overlap matcher.

Computes a Jaccard-style score on the lemmatised token sets of each
requirement / clause pair. No external dependencies — pure stdlib.

This is the cheapest fuzzy matcher. It catches links the explicit-id
matcher misses (where the spec author paraphrased the clause rather than
citing it), but it's also the noisiest. The combiner downweights its score
relative to the more discriminating matchers via a default weight.
"""

from __future__ import annotations

import re
from typing import List, Set

from ..models import DDERow, Match


# Tokens shorter than 3 chars or in this stopword list are dropped
# before scoring.
_STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "from", "by", "as", "at", "be", "is", "are", "was", "were", "been",
    "shall", "must", "should", "may", "can", "will", "not", "all", "any",
    "this", "that", "these", "those", "such", "each", "per", "via",
    "into", "onto", "out", "up", "down", "than", "then", "but", "if",
    "so", "no", "yes", "we", "you", "they", "it", "its", "their", "his",
    "her", "him", "she", "he", "i", "me", "my", "our", "us",
}

_TOKEN = re.compile(r"[A-Za-z][A-Za-z\-]+")


def _tokenise(text: str | None) -> Set[str]:
    if not text:
        return set()
    return {
        t.lower()
        for t in _TOKEN.findall(text)
        if len(t) >= 3 and t.lower() not in _STOPWORDS
    }


def run(
    contract_rows: List[DDERow],
    procedure_rows: List[DDERow],
    threshold: float = 0.15,
) -> List[Match]:
    """Return one ``Match`` per (req, clause) whose Jaccard ≥ threshold.

    Threshold defaults to 0.15 — empirically the lowest level where the
    signal-to-noise stays useful for spec / procedure pairs. Tune lower
    for short clauses (a single-sentence clause shares few tokens by
    definition) or higher to suppress noise.
    """

    procedure_tokens = [
        (clause, _tokenise(clause.text)) for clause in procedure_rows
    ]

    matches: List[Match] = []
    for req in contract_rows:
        req_tokens = _tokenise(req.text)
        if not req_tokens:
            continue
        for clause, clause_tokens in procedure_tokens:
            if not clause_tokens:
                continue
            shared = req_tokens & clause_tokens
            if not shared:
                continue
            union = req_tokens | clause_tokens
            score = len(shared) / len(union)
            if score < threshold:
                continue
            top_terms = ", ".join(sorted(shared)[:6])
            matches.append(
                Match(
                    contract_id=req.stable_id,
                    procedure_id=clause.stable_id,
                    matcher="keyword_overlap",
                    score=score,
                    evidence=f"shared terms: {top_terms}",
                )
            )
    return matches
