"""Read DDE xlsx workbooks into nimbus-skeleton ``DDERow`` records.

Thin wrapper over the shared ``process_tools_common.dde_xlsx`` package.
The shared module yields a full superset of fields per row; this
module filters to the subset the skeleton builder needs (no
``block_ref`` / ``keywords`` / ``confidence`` / ``notes`` / ``context``
— those add no value to a swimlane-and-flow diagram).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

# Bootstrap: see compliance-matrix/compliance_matrix/loader.py for
# rationale — both consumer tools do the same sys.path dance until
# one of them picks up pyproject.toml and the others can pip-install
# the common package as an editable dep.
_COMMON_ROOT = Path(__file__).resolve().parents[2] / "process-tools-common"
if _COMMON_ROOT.is_dir() and str(_COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(_COMMON_ROOT))

from process_tools_common.dde_xlsx import (  # noqa: E402
    iter_dde_records,
    load_actor_aliases,
)

from .models import DDERow


# Subset of fields the skeleton builder needs.
_ALLOWED_FIELDS = {
    "stable_id",
    "text",
    "source_file",
    "heading_trail",
    "section",
    "row_ref",
    "primary_actor",
    "secondary_actors",
    "polarity",
    "req_type",
}


def load_dde_xlsx(path):
    """Load a DDE requirements workbook in source-document order."""

    out: List[DDERow] = []
    for record in iter_dde_records(path):
        filtered = {k: v for k, v in record.items() if k in _ALLOWED_FIELDS}
        out.append(DDERow(**filtered))
    return out


def load_actors_xlsx(path):
    """Load a DDE actors workbook into ``{canonical: [aliases]}``."""

    return load_actor_aliases(path)
