"""Tool-neutral YAML manifest emitter.

The manifest is the project's pivot file — a documented, hand-readable
representation of the skeleton that can be transformed into any target
format (PlantUML, BPMN, Visio .vsdx, native Nimbus import, …) by a
downstream emitter.

Schema (all top-level keys present, even when empty)::

    version: 1
    title: Process Skeleton
    actors: [Operator, System, Supervisor]
    activities:
      - id: REQ-AAA1
        label: log in to control console
        actor: Operator
        flagged: false
    gateways:
      - id: REQ-AAA2-gw
        condition: login successful?
        actor: System
    notes:
      - id: REQ-AAA9
        text: System maintains a 90-day audit log
        actor: System
    flows:
      - [REQ-AAA1, REQ-AAA2-gw]
      - [REQ-AAA2-gw, REQ-AAA2]

YAML is preferred when ``pyyaml`` is available; the function falls back
to a JSON dump (which is also valid YAML 1.2) when it isn't. Manifests
are stable: two runs over the same input produce byte-identical output,
which makes them trivially diffable.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Skeleton


def render(skeleton: Skeleton, title: str = "Process Skeleton") -> str:
    """Return the manifest as a YAML (or JSON-fallback) string."""

    document = {
        "version": 1,
        "title": title,
        "actors": list(skeleton.actors),
        "activities": [
            {
                "id": a.stable_id,
                "label": a.label,
                "actor": a.actor,
                "flagged": a.flagged,
                **({"flag_reason": a.flag_reason} if a.flag_reason else {}),
            }
            for a in skeleton.activities
        ],
        "gateways": [
            {
                "id": g.stable_id,
                "condition": g.condition,
                "actor": g.actor,
            }
            for g in skeleton.gateways
        ],
        "notes": [
            {
                "id": n.stable_id,
                "text": n.text,
                **({"actor": n.actor} if n.actor else {}),
            }
            for n in skeleton.notes
        ],
        "flows": [list(edge) for edge in skeleton.flows],
    }

    try:
        import yaml  # type: ignore

        return yaml.safe_dump(
            document,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=120,
        )
    except ImportError:
        return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def write(skeleton: Skeleton, output_path, title: str = "Process Skeleton") -> None:
    Path(output_path).write_text(render(skeleton, title=title), encoding="utf-8")
