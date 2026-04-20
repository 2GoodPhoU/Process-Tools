"""Requirement detection — classify text as Hard, Soft, or Not-a-requirement.

Hard keywords indicate a binding requirement ("shall", "must", etc.).
Soft keywords indicate advisory or optional language that may still be a
requirement but warrants human review ("should", "may", "can", etc.).
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Keyword sets — tweak these to match your organisation's house style.
HARD_KEYWORDS = {
    "shall",
    "must",
    "will",
    "required",
    "requirement",
    "requirements",
    "mandatory",
    "is to",
    "are to",
}

SOFT_KEYWORDS = {
    "should",
    "may",
    "might",
    "can",
    "could",
    "recommended",
    "preferred",
    "ought to",
}

# Word-boundary patterns (compiled once for speed).
_HARD_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in HARD_KEYWORDS) + r")\b",
    flags=re.IGNORECASE,
)
_SOFT_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in SOFT_KEYWORDS) + r")\b",
    flags=re.IGNORECASE,
)

# Sentence splitter — simple and dependency-free.  Good enough for spec prose.
_SENT_SPLIT_RE = re.compile(r"(?<=[\.\!\?])\s+(?=[A-Z0-9\(\"\'])")


def split_sentences(text: str) -> List[str]:
    """Split a paragraph into sentences.  Preserves bullet-style fragments."""
    text = text.strip()
    if not text:
        return []
    # Collapse whitespace but keep punctuation.
    text = re.sub(r"\s+", " ", text)
    # If the whole text is short and has no terminal punctuation, treat it as
    # a single item (common for table cells and bullet points).
    if len(text) < 400 and not re.search(r"[\.\!\?]", text):
        return [text]
    parts = _SENT_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def classify(text: str) -> Tuple[str, List[str], str]:
    """Classify a sentence.

    Returns (req_type, matched_keywords, confidence).
    req_type is one of "Hard", "Soft", or "" (not a requirement).
    """
    hard_hits = [m.group(1).lower() for m in _HARD_RE.finditer(text)]
    soft_hits = [m.group(1).lower() for m in _SOFT_RE.finditer(text)]

    if hard_hits:
        keywords = sorted(set(hard_hits) | set(soft_hits))
        # Simple confidence heuristic: very short or very long sentences are
        # less likely to be well-formed requirements.
        length = len(text.split())
        if 5 <= length <= 60:
            confidence = "High"
        elif length < 5:
            confidence = "Low"
        else:
            confidence = "Medium"
        return "Hard", keywords, confidence

    if soft_hits:
        keywords = sorted(set(soft_hits))
        return "Soft", keywords, "Medium"

    return "", [], ""
