"""Manual-mapping matcher.

Reads an operator-curated mapping file that says "REQ-AB12 maps to clause
PROC-9F33, PROC-104A". Format is yaml or csv — auto-detected from the
file extension. Manual mappings are the gold-standard signal: when a
human has reviewed and recorded a link, that link should win regardless
of what the fuzzy matchers say. Score is fixed at 1.0.

YAML shape::

    REQ-AB12: [PROC-9F33, PROC-104A]
    REQ-CD34:
      - PROC-2211
      - PROC-77AC

CSV shape (header optional, contract_id,procedure_id columns)::

    contract_id,procedure_id,note
    REQ-AB12,PROC-9F33,reviewed by EY
    REQ-AB12,PROC-104A,
    REQ-CD34,PROC-2211,covers §6.3.1
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional

from ..models import DDERow, Match


def _load_yaml(path: Path) -> List[tuple[str, str, str]]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover — error path
        raise RuntimeError(
            "Manual mapping in YAML format requires PyYAML "
            "(`pip install pyyaml`)"
        ) from exc

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.name}: expected a top-level mapping (contract_id -> "
            "list of procedure_ids)"
        )

    rows: List[tuple[str, str, str]] = []
    for contract_id, procedure_ids in data.items():
        if isinstance(procedure_ids, str):
            procedure_ids = [procedure_ids]
        if not isinstance(procedure_ids, (list, tuple)):
            raise ValueError(
                f"{path.name}: '{contract_id}' must map to a list of "
                "procedure_ids"
            )
        for pid in procedure_ids:
            rows.append((str(contract_id), str(pid), ""))
    return rows


def _load_csv(path: Path) -> List[tuple[str, str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        # Sniff for header by checking the first line.
        first = fh.readline()
        fh.seek(0)
        reader = csv.reader(fh)
        rows_in = list(reader)

    if not rows_in:
        return []

    header_lower = [c.strip().lower() for c in rows_in[0]]
    has_header = "contract_id" in header_lower and "procedure_id" in header_lower

    if has_header:
        c_idx = header_lower.index("contract_id")
        p_idx = header_lower.index("procedure_id")
        n_idx = header_lower.index("note") if "note" in header_lower else None
        body = rows_in[1:]
    else:
        c_idx, p_idx, n_idx = 0, 1, 2 if rows_in and len(rows_in[0]) >= 3 else None
        body = rows_in

    out: List[tuple[str, str, str]] = []
    for row in body:
        if len(row) <= max(c_idx, p_idx):
            continue
        contract_id = row[c_idx].strip()
        procedure_id = row[p_idx].strip()
        if not contract_id or not procedure_id:
            continue
        note = row[n_idx].strip() if n_idx is not None and len(row) > n_idx else ""
        out.append((contract_id, procedure_id, note))
    return out


def run(
    contract_rows: List[DDERow],
    procedure_rows: List[DDERow],
    mapping_path: Optional[str | Path] = None,
) -> List[Match]:
    """Return ``Match`` records for each operator-curated link.

    Returns an empty list when ``mapping_path`` is ``None`` so the matcher
    can be wired into the combiner unconditionally.
    """

    if mapping_path is None:
        return []

    path = Path(mapping_path)
    if not path.exists():
        raise FileNotFoundError(f"manual mapping file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        raw = _load_yaml(path)
    elif suffix == ".csv":
        raw = _load_csv(path)
    else:
        raise ValueError(
            f"unsupported mapping file extension: {suffix} (expected "
            ".yaml/.yml/.csv)"
        )

    valid_contract_ids = {r.stable_id for r in contract_rows}
    valid_procedure_ids = {r.stable_id for r in procedure_rows}

    matches: List[Match] = []
    for contract_id, procedure_id, note in raw:
        if contract_id not in valid_contract_ids:
            continue
        if procedure_id not in valid_procedure_ids:
            continue
        evidence = f"manual mapping ({path.name})"
        if note:
            evidence += f": {note}"
        matches.append(
            Match(
                contract_id=contract_id,
                procedure_id=procedure_id,
                matcher="manual_mapping",
                score=1.0,
                evidence=evidence,
            )
        )
    return matches
