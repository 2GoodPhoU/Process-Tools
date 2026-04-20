"""Actor resolution.

Primary actor comes from the first column of the 2-column table row.
Secondary actors come from (in order of preference):
  1. A user-supplied actors list (Excel file with an "Actor" column, and an
     optional "Aliases" column containing comma-separated alternates).
  2. An optional spaCy-based NER pass (only if the user asked for it and
     spaCy is installed with an English model).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence


@dataclass
class ActorEntry:
    name: str
    aliases: List[str]

    def all_forms(self) -> List[str]:
        forms = [self.name] + [a for a in self.aliases if a]
        return [f.strip() for f in forms if f and f.strip()]


class ActorResolver:
    """Looks up secondary actors in a requirement's text.

    The resolver is deliberately tolerant — it does case-insensitive
    word-boundary matching against every known name/alias and returns a
    deduped list of canonical names.
    """

    def __init__(
        self,
        actors: Optional[Sequence[ActorEntry]] = None,
        use_nlp: bool = False,
    ) -> None:
        self.actors: List[ActorEntry] = list(actors or [])
        self.use_nlp = use_nlp
        self._nlp = None
        if use_nlp:
            self._nlp = _try_load_spacy()

        # Pre-build a single regex for all alias forms, mapped back to canonical
        # names.  This is fast even on large specs.
        self._alias_to_canonical: dict[str, str] = {}
        patterns: List[str] = []
        for entry in self.actors:
            for form in entry.all_forms():
                key = form.lower()
                self._alias_to_canonical[key] = entry.name
                patterns.append(re.escape(form))
        if patterns:
            self._actor_re = re.compile(
                r"\b(" + "|".join(patterns) + r")\b",
                flags=re.IGNORECASE,
            )
        else:
            self._actor_re = None

    def resolve(self, text: str, primary: str) -> List[str]:
        found: List[str] = []
        seen: set[str] = set()
        primary_lower = (primary or "").strip().lower()

        if self._actor_re is not None:
            for m in self._actor_re.finditer(text):
                canonical = self._alias_to_canonical[m.group(1).lower()]
                key = canonical.lower()
                if key == primary_lower or key in seen:
                    continue
                seen.add(key)
                found.append(canonical)

        if self._nlp is not None:
            try:
                doc = self._nlp(text)
                for ent in doc.ents:
                    if ent.label_ not in {"PERSON", "ORG", "NORP", "PRODUCT"}:
                        continue
                    name = ent.text.strip()
                    key = name.lower()
                    if not name or key == primary_lower or key in seen:
                        continue
                    seen.add(key)
                    found.append(name)
            except Exception:  # noqa: BLE001 — NLP is best-effort
                pass

        return found


def load_actors_from_xlsx(path: Path) -> List[ActorEntry]:
    """Load an actor list from an Excel file.

    Expected columns (header row, case-insensitive):
        Actor      — canonical name (required)
        Aliases    — comma-separated alternates (optional)
    """
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(c or "").strip().lower() for c in rows[0]]
    try:
        name_col = header.index("actor")
    except ValueError:
        raise ValueError(
            f"{path.name}: expected a header column named 'Actor' in row 1."
        )
    alias_col = header.index("aliases") if "aliases" in header else None

    entries: List[ActorEntry] = []
    for row in rows[1:]:
        if not row or row[name_col] is None:
            continue
        name = str(row[name_col]).strip()
        if not name:
            continue
        aliases: List[str] = []
        if alias_col is not None and row[alias_col] is not None:
            raw = str(row[alias_col])
            aliases = [a.strip() for a in raw.split(",") if a.strip()]
        entries.append(ActorEntry(name=name, aliases=aliases))
    return entries


def _try_load_spacy():
    """Return a loaded spaCy pipeline, or None if unavailable."""
    try:
        import spacy  # type: ignore
    except ImportError:
        return None
    for model in ("en_core_web_sm", "en_core_web_md", "en_core_web_lg"):
        try:
            return spacy.load(model)
        except Exception:  # noqa: BLE001
            continue
    return None
