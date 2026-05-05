"""Multi-action requirement detection + decomposition (0.6.2).

Where 0.6.1's :mod:`compound` module aggregates a modal-verb lead-in plus
a bulleted list into ONE compound requirement, this module solves the
*opposite* problem: a single sentence that carries one modal verb plus
multiple verb phrases joined by ``,`` ... ``, and`` (or ``, or``) is
syntactically one sentence but semantically expresses N atomic
obligations.  Per ISO/IEC/IEEE 29148 5.2.4 (Singular principle) and
the INCOSE *Guide for Writing Requirements*, each requirement should
express one thought.

Eric's canonical case (the field gap that motivated this patch)::

    "Software engineers shall create unit tests, implement CICD
     Pipelines, and integrate software quality control systems."

That is one sentence syntactically, but ``create`` / ``implement`` /
``integrate`` are three distinct actions on three distinct artifacts
- three atomic requirements semantically.

Modes
-----

The module emits a :class:`MultiActionDetection` describing what was
found.  The caller (``parser._walk_content``) decides how to render
that detection based on configuration:

* ``single`` - emit one requirement; behaviour identical to 0.6.1.
  Conservative: source faithfulness wins.
* ``flag``   - emit one requirement with metadata fields populated
  (``multi_action_count``, ``actions``, recommendation note).
  Reviewers see the count and decide per-requirement.
* ``split``  - emit N requirements with hierarchical sub-IDs
  (``REQ-042`` -> ``REQ-042.1``, ``REQ-042.2``, ...).  Each sub-
  requirement carries: same actor, same modal, ONE verb phrase, same
  source line/page, ``parent_id`` populated.

Detection algorithm
-------------------

1. The sentence must contain *exactly one* modal verb token from
   :data:`_MODAL_RE` (``shall`` / ``must`` / ``will`` / ``should``).
   Two modals in one sentence indicate a compound conditional, not a
   multi-action requirement.
2. Splice off everything from (and including) the modal onward.  That
   tail is the action region.
3. spaCy path (when available): build a dependency tree for the tail,
   find the head verb (immediate dependent of the modal - the ROOT
   action), and walk its ``conj`` children with their ``cc``
   conjunctions.  Each ``conj`` chain element + its subtree is one
   verb phrase.  Falls back to regex when spaCy is unavailable
   (matches the offline-fallback pattern from
   :mod:`actor_heuristics`).
4. Regex fallback: split the action region on ``,`` boundaries that
   are followed by another verb phrase (heuristic: a comma followed
   eventually by ``and`` or ``or`` plus an action verb in the next
   chunk).  Returns the verb-phrase list.  For the two-action bare
   ``X or Y`` form (no Oxford comma), splits on the single connector
   when both halves head with a recognisable verb.
5. Disambiguate genuinely-singular compounds: if the verb phrases
   share the SAME action verb (lemma-equivalent), keep as a single
   requirement.  Different action verbs (``create`` / ``implement``
   / ``integrate``) -> split.  Imperfect heuristic (~80% accurate);
   flagged via :attr:`MultiActionDetection.imperfect`.

Caveats / known limitations
---------------------------

* The shared-verb heuristic is a regex-based lemma comparison
  (lower-cased, ``-s``/``-ed``/``-ing`` stripped).  It will miss
  irregular verb forms and won't catch semantic equivalence.  Real
  semantic disambiguation requires an LLM and is out of scope here.
* Verb phrases that share the modal but differ only in object are
  detected as multi-action by :func:`_detect_phrases` but coalesced
  back to a single requirement by :func:`_is_shared_verb`.
* List-of-conditions sentences ("if A, B, and C") are not split -
  they have no action verbs in the post-modal tail, so phrase
  detection returns fewer than ``min_actions`` items.

Pure-helper module: no docx imports, no parser imports.  The pipeline
wiring lives in :mod:`parser`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Modal trigger.  Mirrors compound._MODAL_RE but uses a capture group so
# the caller can locate the modal token's position in the sentence.
# ---------------------------------------------------------------------------


_MODAL_RE = re.compile(
    r"\b(shall|must|will|should)\b",
    flags=re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Action verb cue - used by the regex fallback to confirm that a
# comma-delimited chunk is a verb phrase rather than a noun-list element.
# ---------------------------------------------------------------------------


_VERB_CUE_RE = re.compile(
    r"^\s*(?:and|or|then)?\s*"            # tolerated leading conjunction
    r"(?:not\s+)?"                         # optional negation
    r"([a-z]+(?:e|ed|ing|s)?)\b",          # candidate verb token
    flags=re.IGNORECASE,
)


# Stoplist - words that match _VERB_CUE_RE shape but are clearly not
# action verbs.  Kept short on purpose; we'd rather under-split than
# over-split.  Adding to this list is the pressure-relief valve when
# false-positive splits surface in real specs.
_NOT_A_VERB = frozenset({
    "the", "a", "an", "this", "that", "these", "those",
    "with", "for", "from", "to", "of", "in", "on", "at", "by",
    "and", "or", "but", "nor", "yet",
    "if", "when", "while", "where", "whether", "as",
    "such", "any", "all", "each", "every", "no", "none",
    "less", "more", "most", "least",
    "than", "then",
    # Common noun-list heads that would otherwise pass the cue:
    "mean", "median", "max", "min",
    # Common spec-document noun heads that would otherwise sneak in:
    "policy", "policies", "system", "subsystem", "module", "service",
    "data", "metric", "metrics", "value", "values", "result", "results",
    "document", "documents", "section",
})


# Noun-suffix denylist - tokens ending in any of these are almost
# always derived nouns, not verbs.  Used by :func:`_phrase_head_verb`
# to reject candidates like ``validation`` or ``compliance`` that
# would otherwise pass the shape check.  Conservative on purpose:
# only suffixes that cannot reasonably terminate a base-form English
# verb.  (``ing`` is *not* on this list - gerund-headed verb phrases
# are still valid action heads in spec language.)
_NOUN_SUFFIXES: tuple = (
    # Strongest noun-only suffixes - very rare as base-form verbs.
    "tion", "sion", "ness", "hood",
    # Deliberately NOT included: "ment" (implement, comment, supplement
    # are common spec verbs), "ity"/"ility" (rare verbs but the
    # heuristic can mis-fire on "specificity"-style nouns; we accept
    # the small false-positive risk in exchange for catching them via
    # the explicit _NOT_A_VERB list when needed), "ence"/"ance"
    # (advance/evidence are verbs in some specs).
)


# Phrase-split regex (regex fallback path).
#
# Splits the action region on commas that are followed eventually by an
# explicit ``and`` / ``or`` conjunction (the Oxford-comma terminator).
# We deliberately keep this conservative - splitting on every comma
# would shred prose that happens to contain incidental commas
# ("backed-up, encrypted storage" -> not a multi-action).


_OXFORD_RE = re.compile(
    r"[,;]\s+(?:and|or)\s+",
    flags=re.IGNORECASE,
)


# Bare connector - used for the two-action case where the author wrote
# ``X or Y`` (or ``X and Y``) without an Oxford comma.  Matched only as
# a fallback when no Oxford form is present, and gated by requiring
# both halves to look like verb phrases.
_BARE_CONNECTOR_RE = re.compile(
    r"\s+(?:and|or)\s+",
    flags=re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public dataclasses.
# ---------------------------------------------------------------------------


@dataclass
class MultiActionDetection:
    """One multi-action sentence's decomposition record.

    Stores both the original text (so ``single`` mode can short-circuit
    cleanly) and the ordered list of decomposed phrases.  ``imperfect``
    flags whether the shared-verb disambiguation heuristic could not
    confidently distinguish multi-action from compound - useful for
    reviewer-facing surfacing in ``flag`` mode.
    """

    original_text: str
    actions: List[str] = field(default_factory=list)
    modal: str = ""
    actor_prefix: str = ""           # text BEFORE the modal
    imperfect: bool = False
    via: str = "regex"               # "spacy" | "regex"

    @property
    def count(self) -> int:
        return len(self.actions)

    @property
    def is_multi_action(self) -> bool:
        return self.count >= 2


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------


def _count_modals(text: str) -> int:
    """Number of modal-verb tokens in ``text`` (case-insensitive)."""
    return sum(1 for _ in _MODAL_RE.finditer(text or ""))


def _find_first_modal(text: str) -> Optional[Tuple[int, int, str]]:
    """Return (start, end, matched-token) for the first modal, or None."""
    m = _MODAL_RE.search(text or "")
    if m is None:
        return None
    return m.start(), m.end(), m.group(1)


def _normalise_verb(tok: str) -> str:
    """Lower-case + strip common inflection so ``creates`` and ``create`` match."""
    s = (tok or "").strip().lower()
    if not s:
        return ""
    s = re.sub(r"^(?:and|or|then)\s+", "", s)
    s = re.sub(r"^(?:not\s+)?(?:be|is|are|was|were|been|being|have|has|had)\s+", "", s)
    for suf in ("ing", "ed", "es", "s", "e"):
        if s.endswith(suf) and len(s) > len(suf) + 2:
            s = s[: -len(suf)]
            break
    return s


def _phrase_head_verb(phrase: str) -> str:
    """Extract the head-verb token of a phrase, normalised.

    Returns "" when the phrase has no recognisable verb head.  A head
    token in :data:`_NOT_A_VERB` or ending in a :data:`_NOUN_SUFFIXES`
    suffix is rejected as a noun.
    """
    m = _VERB_CUE_RE.match((phrase or "").strip())
    if m is None:
        return ""
    cue = m.group(1)
    cue_lower = cue.lower()
    if cue_lower in _NOT_A_VERB:
        return ""
    for suf in _NOUN_SUFFIXES:
        if cue_lower.endswith(suf) and len(cue_lower) > len(suf) + 2:
            return ""
    return _normalise_verb(cue)


def _is_shared_verb(phrases: List[str]) -> bool:
    """True iff every phrase has the SAME normalised head verb."""
    heads = [_phrase_head_verb(p) for p in phrases]
    confident = [h for h in heads if h]
    if len(confident) < 2:
        return False
    return all(h == confident[0] for h in confident)


def _strip_trailing_punct(s: str) -> str:
    """Trim trailing ``.,;:`` plus surrounding whitespace."""
    return (s or "").rstrip(" \t.,;:").rstrip()


def _strip_leading_conjunction(s: str) -> str:
    """Drop a leading "and " / "or " / "then " token."""
    return re.sub(r"^\s*(?:and|or|then)\s+", "", s or "", flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# spaCy path - opportunistic; never load-bearing.
# ---------------------------------------------------------------------------


def _try_spacy_phrases(action_region: str) -> Optional[List[str]]:
    """Attempt to split an action region via spaCy's dependency parser.

    Returns the verb-phrase list, or None when spaCy is unavailable or
    the parse didn't yield a usable conj structure.

    Defensive: every step is wrapped so a model that produces an
    unexpected dep shape just falls through to the regex path.
    """
    try:
        import spacy  # type: ignore  # noqa: F401
    except ImportError:
        return None
    try:
        from .actors import _try_load_spacy
    except ImportError:
        return None

    nlp = _try_load_spacy()
    if nlp is None:
        return None
    try:
        doc = nlp(action_region)
    except Exception:  # noqa: BLE001
        return None

    root = None
    for tok in doc:
        if tok.dep_ == "ROOT" and tok.pos_ in {"VERB", "AUX"}:
            root = tok
            break
    if root is None:
        return None

    verb_heads = [root]
    frontier = [root]
    seen = {root.i}
    while frontier:
        nxt = []
        for h in frontier:
            for child in h.children:
                if child.dep_ == "conj" and child.pos_ in {"VERB", "AUX"} and child.i not in seen:
                    verb_heads.append(child)
                    seen.add(child.i)
                    nxt.append(child)
        frontier = nxt

    if len(verb_heads) < 2:
        return None

    phrases: List[str] = []
    for vh in verb_heads:
        toks = sorted(vh.subtree, key=lambda t: t.i)
        while toks and (toks[0].dep_ == "cc" or toks[0].is_punct):
            toks = toks[1:]
        text = " ".join(t.text for t in toks).strip()
        text = _strip_trailing_punct(text)
        if text:
            phrases.append(text)

    if len(phrases) < 2:
        return None
    return phrases


# ---------------------------------------------------------------------------
# Regex fallback - the offline-network load-bearing path.
# ---------------------------------------------------------------------------


def _regex_phrases(action_region: str) -> List[str]:
    """Split an action region into verb phrases using regex heuristics."""
    region = (action_region or "").strip()
    if not region:
        return []

    last_oxford = None
    for m in _OXFORD_RE.finditer(region):
        last_oxford = m
    if last_oxford is None:
        # No Oxford-style connector - try the two-action bare form
        # ("X or Y", "X and Y").  Conservative: only fires when BOTH
        # halves head with a recognisable verb.
        bare = _BARE_CONNECTOR_RE.search(region)
        if bare is None:
            return []
        left = region[: bare.start()].strip()
        right = region[bare.end():].strip()
        if not left or not right:
            return []
        if not _phrase_head_verb(left):
            return []
        if not _phrase_head_verb(right):
            return []
        return [_strip_trailing_punct(left), _strip_trailing_punct(right)]

    head = region[: last_oxford.start()]
    tail = region[last_oxford.end():]

    parts = [p.strip() for p in re.split(r"[,;]", head) if p.strip()]
    parts.append(tail.strip())

    phrases: List[str] = []
    for i, chunk in enumerate(parts):
        chunk = _strip_trailing_punct(chunk)
        if not chunk:
            continue
        head_verb = _phrase_head_verb(chunk)
        if i > 0 and not head_verb:
            if phrases:
                phrases[-1] = (phrases[-1] + ", " + chunk).strip()
            else:
                phrases.append(chunk)
        else:
            phrases.append(chunk)

    cleaned: List[str] = []
    for p in phrases:
        stripped = _strip_leading_conjunction(p).strip()
        head_verb = _phrase_head_verb(stripped)
        if head_verb:
            cleaned.append(stripped)
    return cleaned


# ---------------------------------------------------------------------------
# Public detection entry point.
# ---------------------------------------------------------------------------


def detect(text: str, *, min_actions: int = 2) -> MultiActionDetection:
    """Detect a multi-action requirement.

    Returns a :class:`MultiActionDetection` whose
    :attr:`is_multi_action` property is True iff the sentence carries
    at least ``min_actions`` distinct verb phrases that share a single
    modal.

    The function is wrapped in defensive try/except so any internal
    failure (regex pathology, spaCy model quirk) yields a non-detection
    rather than aborting the parse.
    """
    if not text:
        return MultiActionDetection(original_text=text or "", actions=[])
    try:
        return _detect_inner(text, min_actions=min_actions)
    except Exception:  # noqa: BLE001
        return MultiActionDetection(original_text=text, actions=[])


def _detect_inner(text: str, *, min_actions: int) -> MultiActionDetection:
    modal_count = _count_modals(text)
    if modal_count != 1:
        return MultiActionDetection(original_text=text, actions=[])

    found = _find_first_modal(text)
    if found is None:
        return MultiActionDetection(original_text=text, actions=[])
    start, end, modal = found
    actor_prefix = text[:start]
    action_region = text[end:].lstrip()
    action_region = _strip_trailing_punct(action_region)

    if not _BARE_CONNECTOR_RE.search(action_region):
        return MultiActionDetection(original_text=text, actions=[])

    via = "spacy"
    phrases = _try_spacy_phrases(action_region)
    if phrases is None or len(phrases) < min_actions:
        via = "regex"
        phrases = _regex_phrases(action_region)

    if len(phrases) < min_actions:
        return MultiActionDetection(original_text=text, actions=[])

    shared = _is_shared_verb(phrases)
    if shared:
        return MultiActionDetection(
            original_text=text,
            actions=[],
            modal=modal,
            actor_prefix=actor_prefix,
            imperfect=True,
            via=via,
        )

    return MultiActionDetection(
        original_text=text,
        actions=phrases,
        modal=modal,
        actor_prefix=actor_prefix,
        imperfect=False,
        via=via,
    )


# ---------------------------------------------------------------------------
# Sub-requirement text rendering (split mode).
# ---------------------------------------------------------------------------


def render_sub_requirement(detection: MultiActionDetection, action: str) -> str:
    """Render one atomic sub-requirement text from a detection + action.

    Format::

        "<actor prefix><modal> <verb-phrase>."
    """
    prefix = (detection.actor_prefix or "").rstrip()
    modal = (detection.modal or "shall").strip()
    body = _strip_leading_conjunction((action or "").strip())
    body = _strip_trailing_punct(body)
    if not body:
        return detection.original_text
    parts: List[str] = []
    if prefix:
        parts.append(prefix)
    parts.append(modal)
    parts.append(body)
    out = " ".join(parts).strip()
    if not out.endswith("."):
        out = out + "."
    return out


def render_flag_note(detection: MultiActionDetection) -> str:
    """Reviewer-facing note for ``flag`` mode."""
    n = detection.count
    via = detection.via
    suffix = " (heuristic - verify before splitting)" if detection.imperfect else ""
    return (
        f"Multi-action sentence: {n} verb phrases detected via {via}; "
        f"consider splitting into {n} atomic requirements{suffix}."
    )
