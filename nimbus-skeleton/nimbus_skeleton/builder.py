"""Build a ``Skeleton`` from a list of DDE rows.

Algorithm:

1. Group requirements by primary actor (preserving xlsx row order so the
   resulting flow follows the source document).
2. Per row, run the classifier. ``activity`` → action node;
   ``gateway`` → gateway node + a follow-on action node for the
   conditional clause; ``note`` → annotation.
3. Emit sequence-flow edges between consecutive nodes within the same
   actor's swimlane. Cross-actor handoffs are emitted when the actor
   changes between consecutive rows.

The builder doesn't try to detect loops, parallel branches, or merge
points — those require human judgment that we explicitly defer to the
review pass. Anything ambiguous gets ``flagged=True`` on the activity
and lands in the review-side-car xlsx.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence

from .classifier import classify
from .models import Activity, DDERow, Gateway, Note, Skeleton


_DEFAULT_ACTOR = "(Unassigned)"


def build_skeleton(
    rows: Sequence[DDERow],
    actors_overrides: Optional[dict[str, list[str]]] = None,
) -> Skeleton:
    """Turn DDE rows into a ``Skeleton``.

    ``actors_overrides`` is the parsed DDE actors workbook (canonical
    name → aliases). When supplied, the builder maps the row's
    ``primary_actor`` field through the alias table so two requirements
    that say 'Operator' and 'the operator' end up in the same swimlane.
    """

    actors_overrides = actors_overrides or {}
    alias_to_canonical = _build_alias_index(actors_overrides)

    skeleton = Skeleton()
    last_node_per_actor: dict[str, str] = {}
    last_node_global: Optional[tuple[str, str]] = None  # (stable_id, actor)

    for row in rows:
        actor = _resolve_actor(row.primary_actor, alias_to_canonical)

        cls = classify(row.text, polarity=row.polarity)
        if cls.kind == "note":
            skeleton.add_note(Note(stable_id=row.stable_id, text=cls.label, actor=actor))
            continue

        if cls.kind == "gateway":
            condition = _extract_condition(row.text)
            gateway = Gateway(
                stable_id=row.stable_id + "-gw",
                condition=condition,
                actor=actor,
            )
            skeleton.add_gateway(gateway)
            # The action that follows the conditional becomes its own
            # activity node so the diagram shows: gateway → activity.
            activity = Activity(
                stable_id=row.stable_id,
                label=cls.label,
                actor=actor,
                flagged=True,
                flag_reason="conditional requirement — confirm gateway branch labels",
            )
            skeleton.add_activity(activity)
            skeleton.flows.append((gateway.stable_id, activity.stable_id))

            # Wire previous in-actor node to the gateway.
            prev = last_node_per_actor.get(actor)
            if prev:
                skeleton.flows.append((prev, gateway.stable_id))
            elif last_node_global is not None and last_node_global[1] != actor:
                skeleton.flows.append((last_node_global[0], gateway.stable_id))
            last_node_per_actor[actor] = activity.stable_id
            last_node_global = (activity.stable_id, actor)
            continue

        # Default: an activity.
        activity = Activity(
            stable_id=row.stable_id,
            label=cls.label,
            actor=actor,
            flagged=cls.flagged,
            flag_reason=cls.flag_reason,
        )
        skeleton.add_activity(activity)

        prev = last_node_per_actor.get(actor)
        if prev:
            skeleton.flows.append((prev, activity.stable_id))
        elif last_node_global is not None and last_node_global[1] != actor:
            # Cross-actor handoff
            skeleton.flows.append((last_node_global[0], activity.stable_id))
        last_node_per_actor[actor] = activity.stable_id
        last_node_global = (activity.stable_id, actor)

    return skeleton


def _resolve_actor(
    raw: Optional[str], alias_index: dict[str, str]
) -> str:
    if not raw:
        return _DEFAULT_ACTOR
    raw_clean = raw.strip()
    if not raw_clean:
        return _DEFAULT_ACTOR
    return alias_index.get(raw_clean.lower(), raw_clean)


def _build_alias_index(
    actors_overrides: dict[str, list[str]]
) -> dict[str, str]:
    """``{lowercase_alias: canonical_name}`` for fast lookup."""

    index: dict[str, str] = {}
    for canonical, aliases in actors_overrides.items():
        index[canonical.lower()] = canonical
        for alias in aliases:
            index[alias.lower()] = canonical
    return index


_CONDITIONAL_CAPTURE = re.compile(
    r"\b(?:if|when|unless|in case of|in the event (?:that|of)|"
    r"provided that|whenever)\b\s+([^,;.]+)",
    flags=re.IGNORECASE,
)


def _extract_condition(text: str) -> str:
    """Pull the conditional clause out of a requirement's text. Falls
    back to a generic label if the regex doesn't catch a clean phrase."""

    hit = _CONDITIONAL_CAPTURE.search(text)
    if hit is None:
        return "(condition — review)"
    cond = hit.group(1).strip()
    cond = " ".join(cond.split())
    if len(cond) > 70:
        cond = cond[:69].rstrip(",;:") + "…"
    return cond + "?"
