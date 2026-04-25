"""Fuzzy-ID matcher — tolerant section-number matching.

Extends the explicit_id matcher to handle typos and format variations in
stable IDs and section numbers. For example:

- "DO-178C §6.3.1" (with special char) vs "DO-178C 6.3.1" (plain)
- "Section 4.2" (missing final digit) vs "4.2.1" (in procedure)
- "6-3-1" (dashes) vs "6.3.1" (dots)

Uses Levenshtein distance to score near-misses, with a configurable
threshold (default: 0.90, meaning 90% string similarity required).

This is a greedy matcher — it picks the best fuzzy match for each
requirement even if the score is modest. Use with lower confidence
than explicit_id (weighted at 0.60 instead of 1.00).
"""

from __future__ import annotations

import re
from typing import Iterable, List, Set

from ..models import DDERow, Match


# Normalized section-number pattern: remove special chars, normalize separators
_SECTION_NUM = re.compile(r"\b\d+(?:[.\-/]\d+){0,4}\b")


def _levenshtein_distance(a: str, b: str) -> int:
    """Compute Levenshtein distance between two strings (edit distance)."""
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)

    previous_row = range(len(b) + 1)
    for i, c1 in enumerate(a):
        current_row = [i + 1]
        for j, c2 in enumerate(b):
            # j+1 instead of j since previous_row and current_row are one character longer
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _similarity_score(a: str, b: str) -> float:
    """Return similarity as a float in [0, 1] based on Levenshtein distance.
    1.0 = identical, 0.0 = completely different."""
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    distance = _levenshtein_distance(a, b)
    return 1.0 - (distance / max_len)


def _normalize_id(text: str) -> str:
    """Normalize an ID or section number for fuzzy matching.
    
    Removes special characters, collapses multiple separators, and lowercases.
    Examples:
      "DO-178C §6.3.1" → "do178c631"
      "6.3.1"          → "631"
      "Section 4.2"    → "section42"
    """
    # Remove non-alphanumeric except digits and letters; collapse runs
    normalized = re.sub(r"[^a-z0-9]+", "", text.lower())
    return normalized


def _candidate_tokens(clause: DDERow) -> Set[str]:
    """Tokens from clause that could match a contract requirement, with fuzzy tolerance."""
    tokens: Set[str] = {clause.stable_id}
    
    # Extract section numbers from various fields
    for field in (clause.row_ref, clause.heading_trail, clause.section):
        if not field:
            continue
        for hit in _SECTION_NUM.findall(field):
            # Add the raw match plus normalized version
            tokens.add(hit)
            tokens.add(_normalize_id(hit))
    
    return tokens


def run(
    contract_rows: List[DDERow],
    procedure_rows: List[DDERow],
    threshold: float = 0.90,
) -> List[Match]:
    """Fuzzy-match contract requirements against procedure clauses.
    
    Args:
        contract_rows: list of contract requirements
        procedure_rows: list of procedure clauses
        threshold: minimum similarity (0.0–1.0) to report a match.
                  Default 0.90 means 90% similar.
    
    Returns:
        list of Match objects with fuzzy_id matcher and scores in [0, 1]
    """
    matches: List[Match] = []
    
    for clause in procedure_rows:
        clause_tokens = _candidate_tokens(clause)
        clause_normalized = _normalize_id(clause.stable_id)
        
        for req in contract_rows:
            haystack = " ".join(filter(None, (req.text, req.context or "")))
            if not haystack:
                continue
            
            # Extract potential matches from the requirement text
            # (ID-like tokens and section numbers)
            req_tokens = set(re.findall(r"\b[A-Z0-9\.\-/]+\b", haystack))
            req_normalized_tokens = {_normalize_id(t) for t in req_tokens}
            
            best_score = 0.0
            best_match = None
            
            # Try each procedure token against each requirement token
            for proc_token in clause_tokens:
                proc_normalized = _normalize_id(proc_token)
                for req_token in req_normalized_tokens:
                    score = _similarity_score(proc_normalized, req_token)
                    if score > best_score:
                        best_score = score
                        best_match = (proc_token, req_token, score)
            
            # Report if we crossed the threshold
            if best_score >= threshold:
                proc_token, req_token, score = best_match
                evidence = f"fuzzy match: '{proc_token}' ≈ '{req_token}' ({score:.2%} similar)"
                matches.append(
                    Match(
                        contract_id=req.stable_id,
                        procedure_id=clause.stable_id,
                        matcher="fuzzy_id",
                        score=best_score,
                        evidence=evidence,
                    )
                )
    
    return matches
