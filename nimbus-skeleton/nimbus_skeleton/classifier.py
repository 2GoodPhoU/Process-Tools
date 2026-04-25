"""Decide whether a DDE requirement becomes an activity, a gateway, or a note.

The decision drives swimlane / arrow / decision-shape generation. It's
deliberately lightweight — regex against modal-keyword and conditional-
keyword lists. False positives flow through to the activity diagram with
``flagged=True`` so the reviewer sees them; false negatives drop into the
notes section with a hint at the source row.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# Modal verbs that indicate an actor performing an action. The leading
# pronoun / actor noun is captured by the surrounding context — we just
# need *something* in the text that says 'an action happens here'.
_IMPERATIVE_KEYWORDS = re.compile(
    r"\b(?:shall|must|will|should|may|can|is required to|are required to|"
    r"need to|needs to)\b",
    flags=re.IGNORECASE,
)

# Conditional / branching cues. When one of these appears, the
# requirement likely encodes a decision and the builder emits a gateway.
_CONDITIONAL_KEYWORDS = re.compile(
    r"\b(?:if|when|unless|in case of|in the event (?:that|of)|"
    r"provided that|whenever|otherwise|else)\b",
    flags=re.IGNORECASE,
)

# Heuristic: pure declarative / definitional language with no action
# verb. These become notes rather than activities.
_DECLARATIVE_HINT = re.compile(
    r"\b(?:is responsible for|is defined as|consists of|comprises|"
    r"contains|includes|refers to|means)\b",
    flags=re.IGNORECASE,
)


@dataclass
class Classification:
    kind: str          # "activity" | "gateway" | "note"
    label: str         # short human-friendly label for the diagram
    flagged: bool = False
    flag_reason: Optional[str] = None


def classify(text: str, polarity: Optional[str] = None) -> Classification:
    """Categorise a requirement.

    ``polarity`` carries DDE's Positive / Negative tag. A negative
    requirement ('the operator shall NOT bypass the safety check') is
    still an activity from the diagram's perspective — but it should be
    flagged for review because rendering it cleanly in an activity
    diagram usually means a constraint, not an action.
    """

    if not text:
        return Classification(kind="note", label="(empty requirement)", flagged=True,
                              flag_reason="empty text")

    has_imperative = bool(_IMPERATIVE_KEYWORDS.search(text))
    has_conditional = bool(_CONDITIONAL_KEYWORDS.search(text))
    has_declarative = bool(_DECLARATIVE_HINT.search(text))
    is_negative = (polarity or "").strip().lower() == "negative"

    label = _short_label(text)

    if has_conditional and has_imperative:
        # Conditional + action → gateway followed by activity. The
        # builder splits this into two nodes; we tag as 'gateway' here
        # and the builder does the split.
        return Classification(kind="gateway", label=label)

    if has_imperative:
        flagged = is_negative
        return Classification(
            kind="activity",
            label=label,
            flagged=flagged,
            flag_reason="negative polarity — render as constraint, not flow"
            if flagged
            else None,
        )

    if has_declarative and not has_imperative:
        return Classification(kind="note", label=label)

    # No clear modal verb and no declarative hint. Best guess: it's an
    # activity, but flag it so the reviewer confirms.
    return Classification(
        kind="activity",
        label=label,
        flagged=True,
        flag_reason="no modal verb detected — confirm this is an action",
    )


def _short_label(text: str, max_chars: int = 80) -> str:
    """Diagram-friendly label: trim to first sentence, then to max chars."""

    # Take the first sentence (period / question / exclamation).
    end = re.search(r"[.!?](?:\s|$)", text)
    label = text[: end.start()] if end else text

    label = " ".join(label.split())  # collapse whitespace
    if len(label) > max_chars:
        cut = label[: max_chars - 1]
        last_space = cut.rfind(" ")
        if last_space > max_chars * 0.5:
            cut = cut[:last_space]
        label = cut.rstrip(",;:") + "…"
    return label
