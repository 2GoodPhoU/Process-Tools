"""Combine per-matcher ``Match`` records into a single per-pair score.

Combination strategy: for each (contract_id, procedure_id) pair where any
matcher fired, the combined score is the max of the per-matcher scores
(after weighting). This prefers to surface a strong manual mapping or a
strong explicit-id hit over a thin keyword overlap, while still showing
the lower-signal matchers' votes via the evidence list.

Default weights:

    explicit_id     1.00   gold standard
    manual_mapping  1.00   gold standard
    similarity      0.85   solid signal but tunable
    keyword_overlap 0.65   noisy, downweighted

The weights only affect the *combined* score, never the per-matcher
votes recorded on the ``CombinedMatch``. A matcher that returned 0.4
with weight 0.65 contributes a weighted score of 0.26 toward the max.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from .models import CombinedMatch, Match


DEFAULT_WEIGHTS: Dict[str, float] = {
    "explicit_id": 1.0,
    "manual_mapping": 1.0,
    "similarity": 0.85,
    "keyword_overlap": 0.65,
}


def combine(
    matches: Iterable[Match],
    weights: Dict[str, float] | None = None,
) -> Dict[Tuple[str, str], CombinedMatch]:
    """Aggregate per-matcher matches into per-pair combined records."""

    weights = weights or DEFAULT_WEIGHTS
    out: Dict[Tuple[str, str], CombinedMatch] = {}

    for match in matches:
        key = (match.contract_id, match.procedure_id)
        weight = weights.get(match.matcher, 0.5)
        weighted = match.score * weight

        record = out.get(key)
        if record is None:
            out[key] = CombinedMatch(
                contract_id=match.contract_id,
                procedure_id=match.procedure_id,
                score=weighted,
                matchers=[match.matcher],
                evidence=[f"[{match.matcher}] {match.evidence}"],
            )
            continue

        if weighted > record.score:
            record.score = weighted
        if match.matcher not in record.matchers:
            record.matchers.append(match.matcher)
        record.evidence.append(f"[{match.matcher}] {match.evidence}")

    return out
