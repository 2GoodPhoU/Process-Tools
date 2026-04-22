"""Requirement detection — classify text as Hard, Soft, or Not-a-requirement.

Hard keywords indicate a binding requirement ("shall", "must", etc.).
Soft keywords indicate advisory or optional language that may still be a
requirement but warrants human review ("should", "may", "can", etc.).

Both keyword sets can be tuned at runtime by constructing a
``KeywordMatcher`` with custom add/remove lists (wired up through
``requirements_extractor.config.KeywordsConfig``).  The module-level
``classify`` / ``split_sentences`` helpers remain for backward
compatibility and use the built-in defaults.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Set, Tuple

# Built-in defaults — tweak these (or better, override via Config) to match
# your organisation's house style.
#
# Curation notes:
#   - ``will`` is deliberately SOFT, not HARD.  Future-tense prose ("This
#     document will serve as a guide") commonly trips it, so we capture
#     "will" sentences for review rather than treating them as binding.
#   - Bare nouns ``requirement`` / ``requirements`` are intentionally NOT
#     in the list — sentences like "This requirement is tracked in JIRA"
#     match nothing useful.  The adjective form ``required`` stays in.
HARD_KEYWORDS: Set[str] = {
    "shall",
    "must",
    "required",
    "mandatory",
    "is to",
    "are to",
}

SOFT_KEYWORDS: Set[str] = {
    "should",
    "may",
    "might",
    "can",
    "could",
    "will",
    "recommended",
    "preferred",
    "ought to",
}


# Words that negate a preceding modal keyword.  Split into two flavours:
#   * SPACED — "not", "never" — appear as their own token after the modal
#     (and optionally after one intervening filler word).
#   * SUFFIX — "n't" (with either ASCII or curly apostrophe) — attach
#     directly to the modal with no whitespace.  The leading 'n' is
#     optional because some modals already end in n, e.g. "can" + "'t"
#     for "can't" vs. "should" + "n't" for "shouldn't".
_NEGATION_SPACED = (r"not", r"never")
_NEGATION_SUFFIX = r"n?[\u2019']t"


# Sentence splitter — simple and dependency-free.  Good enough for spec prose.
_SENT_SPLIT_RE = re.compile(r"(?<=[\.\!\?])\s+(?=[A-Z0-9\(\"\'])")


def split_sentences(text: str) -> List[str]:
    """Split a paragraph into sentences.  Preserves bullet-style fragments."""
    text = (text or "").strip()
    if not text:
        return []
    text = re.sub(r"\s+", " ", text)
    # If the whole text is short and has no terminal punctuation, treat it as
    # a single item (common for table cells and bullet points).
    if len(text) < 400 and not re.search(r"[\.\!\?]", text):
        return [text]
    parts = _SENT_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# KeywordMatcher — configurable classifier.
# ---------------------------------------------------------------------------


class KeywordMatcher:
    """Compiles the HARD/SOFT keyword regexes once, classifies text.

    Construct with ``KeywordMatcher.from_config(config.keywords)`` to honour
    user-supplied add/remove lists, or ``KeywordMatcher.default()`` for the
    built-in behaviour.
    """

    def __init__(self, hard: Iterable[str], soft: Iterable[str]) -> None:
        self.hard: Set[str] = {k.lower() for k in hard if k and k.strip()}
        self.soft: Set[str] = {k.lower() for k in soft if k and k.strip()}
        # When a word lives in both sets we trust the hard classification —
        # but also filter it out of soft to keep behaviour predictable.
        self.soft -= self.hard
        self._hard_re = self._compile(self.hard)
        self._soft_re = self._compile(self.soft)
        self._negation_re = self._compile_negation(self.hard | self.soft)

    @staticmethod
    def _compile(words: Iterable[str]) -> "re.Pattern[str] | None":
        ws = [w for w in words if w]
        if not ws:
            return None
        # Sort longer alternatives first so 'ought to' wins over 'ought'.
        ws = sorted(ws, key=len, reverse=True)
        return re.compile(
            r"\b(" + "|".join(re.escape(w) for w in ws) + r")\b",
            flags=re.IGNORECASE,
        )

    @staticmethod
    def _compile_negation(words: Iterable[str]) -> "re.Pattern[str] | None":
        """Compile a regex that matches any known keyword immediately
        followed by a negation word.

        Matches: "shall not", "must not", "may not", "should never",
        "can't" (via the ``n't`` suffix form), "will not"…

        Single-word modals are the common case; we allow at most one short
        filler word between the modal and a spaced negation ("shall clearly
        not", "may sometimes never") to stay precise.  The ``n't`` suffix
        form attaches directly to the modal with no space.
        """
        ws = [w for w in words if w]
        if not ws:
            return None
        ws = sorted(ws, key=len, reverse=True)
        kw_alt = "|".join(re.escape(w) for w in ws)
        spaced_alt = "|".join(_NEGATION_SPACED)
        # Two branches joined by alternation:
        #   1. modal + optional filler + spaced negation ("shall not")
        #   2. modal directly suffixed by n't ("can't", "won't")
        return re.compile(
            rf"\b(?:{kw_alt})"
            rf"(?:(?:\s+\w{{1,20}})?\s+(?:{spaced_alt})\b|{_NEGATION_SUFFIX}\b)",
            flags=re.IGNORECASE,
        )

    def classify(self, text: str) -> Tuple[str, List[str], str]:
        """Classify a sentence.

        Returns (req_type, matched_keywords, confidence).
        req_type is one of "Hard", "Soft", or "" (not a requirement).
        """
        hard_hits = (
            [m.group(1).lower() for m in self._hard_re.finditer(text)]
            if self._hard_re is not None else []
        )
        soft_hits = (
            [m.group(1).lower() for m in self._soft_re.finditer(text)]
            if self._soft_re is not None else []
        )

        if hard_hits:
            keywords = sorted(set(hard_hits) | set(soft_hits))
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

    def is_negative(self, text: str) -> bool:
        """Return True iff a known keyword is immediately negated in ``text``.

        Examples that match:
            "The system shall not reboot."
            "Users must not log in without MFA."
            "Operators may never override a lockout."
            "The service can't accept blank inputs."  # n['\u2019]t form
        """
        if self._negation_re is None:
            return False
        return bool(self._negation_re.search(text))

    # ---- Factories ---------------------------------------------------- #

    @classmethod
    def default(cls) -> "KeywordMatcher":
        return cls(hard=HARD_KEYWORDS, soft=SOFT_KEYWORDS)

    @classmethod
    def from_config(cls, kw_cfg) -> "KeywordMatcher":
        """Build from a ``config.KeywordsConfig``.

        Applies add/remove lists (case-insensitive) on top of the built-in
        defaults.  Accepts ``None`` for the defaults-only case.
        """
        if kw_cfg is None:
            return cls.default()
        hard = _apply_add_remove(HARD_KEYWORDS, kw_cfg.hard_add, kw_cfg.hard_remove)
        soft = _apply_add_remove(SOFT_KEYWORDS, kw_cfg.soft_add, kw_cfg.soft_remove)
        return cls(hard=hard, soft=soft)


def _apply_add_remove(
    baseline: Iterable[str],
    add: Iterable[str],
    remove: Iterable[str],
) -> Set[str]:
    remove_lower = {r.strip().lower() for r in remove if r and r.strip()}
    out = {k.lower() for k in baseline if k.lower() not in remove_lower}
    for a in add or []:
        if a and a.strip():
            out.add(a.strip().lower())
    return out


# ---------------------------------------------------------------------------
# Module-level convenience wrappers (kept for any external callers).
# ---------------------------------------------------------------------------


_DEFAULT_MATCHER = KeywordMatcher.default()


def classify(text: str) -> Tuple[str, List[str], str]:
    """Classify using the built-in HARD/SOFT keyword lists."""
    return _DEFAULT_MATCHER.classify(text)


def is_negative(text: str) -> bool:
    """Detect negation using the built-in HARD/SOFT keyword lists."""
    return _DEFAULT_MATCHER.is_negative(text)
