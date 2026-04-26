"""Read DDE xlsx workbooks into compliance-matrix ``DDERow`` instances.

Thin wrapper over the shared ``process_tools_common.dde_xlsx`` package
that handles the actual xlsx reading and the iterate-and-filter loop.
This module's job is just to attach the ``side`` discriminator
("contract" or "procedure") that the matchers and writer rely on.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

# Bootstrap: add the sibling process-tools-common package to sys.path
# so the import below works regardless of how this tool is invoked
# (CLI, unit test, GUI launcher). Each tool in Process-Tools/ does the
# same dance — once any of them gets pip-packaged this can go away.
_COMMON_ROOT = Path(__file__).resolve().parents[2] / "process-tools-common"
if _COMMON_ROOT.is_dir() and str(_COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(_COMMON_ROOT))

from process_tools_common.dde_xlsx import load_into  # noqa: E402

from .models import DDERow


# Fields the compliance-matrix DDERow understands. The shared loader
# may yield additional keys; load_into() filters to this whitelist
# before constructing each DDERow so future DDE schema additions
# don't break this consumer.
_ALLOWED_FIELDS = {
    "stable_id",
    "text",
    "source_file",
    "heading_trail",
    "section",
    "row_ref",
    "block_ref",
    "primary_actor",
    "secondary_actors",
    "req_type",
    "polarity",
    "keywords",
    "confidence",
    "notes",
    "context",
}


def load_dde_xlsx(path: str | Path, side: str = "contract") -> List[DDERow]:
    """Load a DDE xlsx into a list of compliance-matrix ``DDERow``.

    ``side`` is "contract" or "procedure" — controls which half of the
    matrix this file represents.
    """

    def _factory(**kw):
        return DDERow(side=side, **kw)

    return load_into(path, _factory, fields=_ALLOWED_FIELDS)


def load_pair(
    contract_path: str | Path, procedure_path: str | Path
) -> Tuple[List[DDERow], List[DDERow]]:
    """Convenience helper — load both sides in one call."""

    return (
        load_dde_xlsx(contract_path, side="contract"),
        load_dde_xlsx(procedure_path, side="procedure"),
    )
