"""Rule-based actor-extraction heuristics (NLP-fallback path).

The :class:`~requirements_extractor.actors.ActorResolver` already covers
two passes for finding *secondary* actors in a requirement's text:

1. ``regex`` -- alias matching against a user-supplied actors list.
2. ``nlp``   -- spaCy NER, when spaCy + an English model are installed.

Both have a hard floor: pass 1 needs a seed list, pass 2 needs NLP. On
the offline-network-default deployment target (Eric's defense site, no
pip install at runtime) NLP is unavailable; on a fresh project there is
also no seed list yet. Without those, secondary-actor extraction returns
nothing -- even when the requirement text obviously names another actor.

This module is the third pass: hand-rolled regex heuristics that
extract role/actor candidates from prose alone. Each rule is small,
documented inline with the example sentence it targets, and has a
matching regression test in ``tests/test_actor_heuristics.py``.

Design constraints:

- **Additive, not replacement.** When NLP is available we still prefer
  it; this pass is run last and dedupes against earlier hits.
- **Conservative.** False positives are worse than false negatives here
  -- the reviewer audits the output xlsx, and noise costs them time.
  When in doubt, drop the candidate.
- **Pure functions.** Each heuristic is a pure ``str -> List[str]``
  function so the unit tests can pin behaviour cheaply.
- **No dependencies.** Stdlib ``re`` only -- this layer must work in
  the no-NLP build.

The orchestration is exposed via :func:`extract_actor_candidates`,
which runs every heuristic and returns a deduped list of canonical-
shaped actor strings (leading determiner stripped, trailing possessive
stripped). It is *not* wired into ActorResolver by default -- callers
opt in by passing ``use_heuristics=True`` so existing test fixtures
that depend on the no-secondary-actor behaviour stay green.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional


# ---------------------------------------------------------------------------
# Tunables.
# ---------------------------------------------------------------------------


#: Words that strongly signal a noun phrase is a role/actor when they
#: appear as the head noun of a Title-case multi-word phrase. Defense /
#: aerospace specs lean heavily on these. Keep this list tight -- false
#: positives here are how this whole module gets tuned out by users.
_ROLE_HEAD_NOUNS = frozenset({
    "Service", "System", "Subsystem", "Module", "Manager", "Engine",
    "Console", "Controller", "Operator", "Administrator", "Officer",
    "Engineer", "Reviewer", "Approver", "Supervisor", "Auditor",
    "Inspector", "Specialist", "Technician", "Analyst", "Logger",
    "Gateway", "Server", "Client", "Node", "Agent", "Component",
    "Department", "Team", "Group", "Office", "Unit", "Bureau",
    "Authority", "Contractor", "Vendor", "Customer", "User",
    "Application", "Database", "Repository", "Pipeline", "Handler",
    "Processor", "Scheduler", "Dispatcher", "Sensor", "Actuator",
    "Device", "Terminal", "Workstation", "Display", "Panel",
    "Interface", "API", "Endpoint",
})


#: Stopwords disallowed at the head-noun position even when capitalised.
#: Sentences sometimes begin with capitalised function words ("If",
#: "When", "After") -- those are not actors. Standalone presence after
#: a determiner is also nonsense ("the The"), so we drop these.
_HEAD_STOPWORDS = frozenset({
    "If", "When", "After", "Before", "Once", "Until", "While",
    "Where", "Whenever", "Although", "Though", "Because", "Since",
    "The", "A", "An", "This", "That", "These", "Those",
    "It", "He", "She", "They",
    "Note", "Notes", "Section", "Table", "Figure", "Appendix",
    "Step", "Steps", "Action", "Actions", "Required",
})


#: Role-suffix endings -- a Title-case word ending in any of these
#: (case-sensitive on the suffix part) is taken as a role even if its
#: head noun isn't in :data:`_ROLE_HEAD_NOUNS`. ``-er``/``-or``/``-ist``
#: are the workhorse English agent-noun morphemes.
_ROLE_SUFFIXES = ("er", "or", "ist", "ant", "ent")


# ---------------------------------------------------------------------------
# Shared cleanup -- mirrors :func:`actors.canonicalise_ner_name` so this
# module's output is comparable to NER hits without re-canonicalising.
# ---------------------------------------------------------------------------


_LEADING_DETS = ("the ", "a ", "an ", "The ", "A ", "An ")
_TRAIL_POSS = ("'s", "’s", "'", "’")


def _clean(raw: str) -> Optional[str]:
    """Strip leading determiner + trailing possessive; return None if junk."""
    if not raw:
        return None
    s = raw.strip()
    # Iterative determiner strip (handles "the the X", rare but cheap).
    while True:
        stripped = False
        for det in _LEADING_DETS:
            if s.startswith(det):
                s = s[len(det):].strip()
                stripped = True
                break
        if not stripped:
            break
    # One pass of possessive strip.
    for poss in _TRAIL_POSS:
        if s.endswith(poss):
            s = s[: -len(poss)].strip()
            break
    if not s:
        return None
    if not any(c.isalnum() for c in s):
        return None
    if s in _HEAD_STOPWORDS:
        return None
    return s


def _is_role_phrase(s: str) -> bool:
    """Cheap test: ``s`` looks like a role / actor name.

    True when:
      * head noun is in :data:`_ROLE_HEAD_NOUNS`, or
      * any token ends in a role-suffix and is Title-case, or
      * it's a single Title-case acronym (``API``, ``GPS``).

    Falls False on lower-case fragments, single-word stop tokens, and
    sentences-that-happen-to-be-capitalised (the head-stopword filter
    catches "If", "When", etc.).
    """
    if not s:
        return False
    tokens = s.split()
    if not tokens:
        return False
    # Single-token acronyms (all caps, length 2-6).
    if (
        len(tokens) == 1
        and 2 <= len(tokens[0]) <= 6
        and tokens[0].isupper()
        and tokens[0].isalpha()
    ):
        return True
    # Head noun (last token) check -- dominant signal.
    head = tokens[-1]
    if head in _ROLE_HEAD_NOUNS:
        return True
    # Role-suffix on a Title-case token (anywhere in the phrase, but
    # most commonly head): "Auditor", "Reviewer", "Operator".
    for tok in tokens:
        if not tok or not tok[0].isupper():
            continue
        for suf in _ROLE_SUFFIXES:
            if tok.endswith(suf) and len(tok) > len(suf) + 1:
                return True
    return False


def _dedupe_keep_order(items: Iterable[str]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


# ---------------------------------------------------------------------------
# Heuristics.  Each function is pure: ``str -> List[str]``.  Naming
# convention: ``_h_<short_name>``.  Inline ``# Example:`` comments give
# the canonical sentence each rule was tuned for -- the regression
# tests echo those examples verbatim so a future change that breaks a
# rule fails loudly.
# ---------------------------------------------------------------------------


# Rule 1: passive-voice "by" agent.
# Example: "The report shall be approved by the Reviewer."
# Example: "Logs are recorded by the Audit Service."
_RULE_BY_AGENT = re.compile(
    r"\b(?:approved|reviewed|signed|verified|recorded|logged|"
    r"validated|inspected|audited|authorised|authorized|certified|"
    r"performed|executed|provided|maintained|generated|sent|"
    r"transmitted|forwarded|received|processed|handled|managed)\s+"
    r"by\s+(?-i:(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3}))",
    flags=re.IGNORECASE,
)


def _h_by_agent(sentence: str) -> List[str]:
    out: List[str] = []
    for m in _RULE_BY_AGENT.finditer(sentence):
        candidate = m.group(1)
        cleaned = _clean(candidate)
        if cleaned and _is_role_phrase(cleaned):
            out.append(cleaned)
    return out


# Rule 2: "send/forward/notify/route X to ACTOR" -- recipient extraction.
# Two surface forms covered:
#   1. "<verb> ... to/of ACTOR"     (send the data to the Logger)
#   2. "<verb> ACTOR"               (notify the Supervisor)
# Each form is its own alternative; the actor-capture is in
# (?-i:...) so [A-Z] stays case-sensitive under the verb-side
# IGNORECASE flag.
_RULE_SEND_TO = re.compile(
    r"\b(?:send|sends|forwards?|routes?|transmits?|delivers?|"
    r"escalates?|reports?|notifies?|notify|informs?|"
    r"alerts?|dispatches?)\b"
    r"(?:"
    # Form 1: with "to" / "of"
    r"(?:\s+(?:the|a|an|its|their|all|any)?\s*\w+(?:\s+\w+){0,3})?\s+"
    r"(?:to|of)\s+(?-i:(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3}))"
    r"|"
    # Form 2: direct-object (notify, inform, alert)
    r"\s+(?-i:(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3}))"
    r")",
    flags=re.IGNORECASE,
)


def _h_send_to(sentence: str) -> List[str]:
    out: List[str] = []
    for m in _RULE_SEND_TO.finditer(sentence):
        # Whichever form fired, the actor lives in group 1 or 2.
        candidate = m.group(1) or m.group(2)
        cleaned = _clean(candidate)
        if cleaned and _is_role_phrase(cleaned):
            out.append(cleaned)
    return out


# Rule 3: possessive-subject form.
# Example: "The Operator's screen shall display the alert."
# Example: "The System's logger shall record every login event."
_RULE_POSSESSIVE = re.compile(
    r"\b(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,2})"
    r"['’]s\b",
)


def _h_possessive(sentence: str) -> List[str]:
    out: List[str] = []
    for m in _RULE_POSSESSIVE.finditer(sentence):
        cleaned = _clean(m.group(1))
        if cleaned and _is_role_phrase(cleaned):
            out.append(cleaned)
    return out


# Rule 4: compound subject "X and Y shall ..." -- both actors named.
# Example: "The Operator and the Supervisor shall co-sign the release."
# Example: "The Auth Service and the Audit Logger shall both record the
#           event."
_RULE_COMPOUND_SUBJECT = re.compile(
    r"^(?:\s*)(?-i:(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,2}))\s+"
    r"and\s+(?-i:(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,2}))\s+"
    r"(?:shall|must|will|should|may)\b",
    flags=re.IGNORECASE,
)


def _h_compound_subject(sentence: str) -> List[str]:
    m = _RULE_COMPOUND_SUBJECT.search(sentence.strip())
    if not m:
        return []
    out: List[str] = []
    for grp in (m.group(1), m.group(2)):
        cleaned = _clean(grp)
        if cleaned and _is_role_phrase(cleaned):
            out.append(cleaned)
    return out


# Rule 5: "If/When ACTOR <verb>" -- conditional-clause subject.
# Example: "If the Auditor approves the change, the System shall deploy."
# Example: "When the Operator presses the kill switch, all motion stops."
_RULE_CONDITIONAL_SUBJECT = re.compile(
    r"\b(?:if|when|whenever|once|after|before)\s+"
    r"(?:the\s+|a\s+|an\s+)"
    r"(?-i:([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3}))\s+"
    r"(?:approves?|rejects?|presses?|authori[sz]es?|signs?|"
    r"submits?|enters?|requests?|cancels?|completes?|closes?|"
    r"opens?|verifies?|confirms?|denies?|accepts?|reviews?|"
    r"detects?|triggers?|initiates?|invokes?|reports?|logs?|"
    r"sends?|fails?|succeeds?)\b",
    flags=re.IGNORECASE,
)


def _h_conditional_subject(sentence: str) -> List[str]:
    out: List[str] = []
    for m in _RULE_CONDITIONAL_SUBJECT.finditer(sentence):
        cleaned = _clean(m.group(1))
        if cleaned and _is_role_phrase(cleaned):
            out.append(cleaned)
    return out


# Rule 6: "for the ACTOR" beneficiary clause.
# Example: "The System shall generate a report for the Compliance Officer."
# NB: deliberately requires a role-shaped phrase to avoid matching
# "for the user to review" (where 'user' is generic + lowercase).
_RULE_FOR_BENEFICIARY = re.compile(
    r"\bfor\s+(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3})",
)


def _h_for_beneficiary(sentence: str) -> List[str]:
    out: List[str] = []
    for m in _RULE_FOR_BENEFICIARY.finditer(sentence):
        cleaned = _clean(m.group(1))
        if cleaned and _is_role_phrase(cleaned):
            out.append(cleaned)
    return out


# Rule 7: implicit-system passive ("shall be logged" with no agent).
# Example: "Every login attempt shall be logged."
# Example: "The transaction is recorded automatically."
# Heuristic: passive verb of an audit/log/record action, with no "by"
# clause -- emit the synthetic actor "(implicit System)" so the
# reviewer sees a hint that someone needs to assign one.
_RULE_IMPLICIT_PASSIVE = re.compile(
    r"\b(?:shall\s+be|must\s+be|will\s+be|is|are)\s+"
    r"(logged|recorded|stored|persisted|archived|audited|tracked|"
    r"captured|monitored|reported)"
    r"(?!.*\bby\b)",
    flags=re.IGNORECASE,
)


def _h_implicit_passive(sentence: str) -> List[str]:
    if _RULE_IMPLICIT_PASSIVE.search(sentence):
        return ["(implicit System)"]
    return []


# Rule 8: "ACTOR-initiated" / "ACTOR-driven" hyphenated form.
# Example: "An Operator-initiated abort shall halt the run."
# Example: "Reviewer-driven approvals are queued for batch processing."
_RULE_HYPHEN_ROLE = re.compile(
    r"\b(?:the\s+|a\s+|an\s+)?"
    r"(?-i:([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,2}))"
    r"-(?:initiated|driven|generated|owned|signed|approved|requested)\b",
    flags=re.IGNORECASE,
)


def _h_hyphenated_role(sentence: str) -> List[str]:
    out: List[str] = []
    for m in _RULE_HYPHEN_ROLE.finditer(sentence):
        cleaned = _clean(m.group(1))
        if cleaned and _is_role_phrase(cleaned):
            out.append(cleaned)
    return out


# Rule 9: "between X and Y" two-actor coordination.
# Example: "Communication between the Operator and the Auth Service
#           shall be encrypted."
_RULE_BETWEEN = re.compile(
    r"\bbetween\s+(?-i:(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3}))\s+"
    r"and\s+(?-i:(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3}))",
    flags=re.IGNORECASE,
)


def _h_between(sentence: str) -> List[str]:
    out: List[str] = []
    for m in _RULE_BETWEEN.finditer(sentence):
        for grp in (m.group(1), m.group(2)):
            cleaned = _clean(grp)
            if cleaned and _is_role_phrase(cleaned):
                out.append(cleaned)
    return out


# Rule 10: appositive role marker: "ACTOR, the SUPER_ROLE,".
# Example: "The QA Lead, the Reviewer, shall countersign the report."
# Tight pattern -- only fires when the appositive itself is role-
# shaped, to avoid grabbing geographical / temporal appositives.
_RULE_APPOSITIVE = re.compile(
    r"\b(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3})"
    r"\s*,\s*(?:the\s+|a\s+|an\s+)?"
    r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3})\s*,",
)


def _h_appositive(sentence: str) -> List[str]:
    out: List[str] = []
    for m in _RULE_APPOSITIVE.finditer(sentence):
        head = _clean(m.group(1))
        appos = _clean(m.group(2))
        # Only fire if at least one of the two halves is role-shaped --
        # otherwise this rule grabs every parenthetical phrase.
        if appos and _is_role_phrase(appos):
            if head and _is_role_phrase(head):
                out.append(head)
            out.append(appos)
        elif head and _is_role_phrase(head) and appos and _is_role_phrase(appos):
            out.append(head)
            out.append(appos)
    return out


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


_ALL_HEURISTICS = (
    _h_by_agent,
    _h_send_to,
    _h_possessive,
    _h_compound_subject,
    _h_conditional_subject,
    _h_for_beneficiary,
    _h_implicit_passive,
    _h_hyphenated_role,
    _h_between,
    _h_appositive,
)


def extract_actor_candidates(
    sentence: str, *, primary: str = "",
) -> List[str]:
    """Return rule-based actor candidates from a single sentence.

    Order is preserved across heuristics; cross-heuristic dedup is
    case-insensitive. ``primary`` (if given) is excluded from the
    output -- this mirrors :class:`ActorResolver`'s convention.
    """
    if not sentence:
        return []
    primary_lower = (primary or "").strip().lower()
    raw: List[str] = []
    for rule in _ALL_HEURISTICS:
        try:
            raw.extend(rule(sentence) or [])
        except re.error:
            # Defensive: a malformed input shouldn't take the run down.
            continue
    out: List[str] = []
    for cand in _dedupe_keep_order(raw):
        if cand.lower() == primary_lower:
            continue
        out.append(cand)
    return out
