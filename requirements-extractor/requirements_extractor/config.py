"""Optional user-supplied configuration for the extractor.

A config file lets users hint at the shape of their documents so the parser
doesn't have to guess, and also exposes knobs for keyword tuning and
content filtering.  Every field is optional; missing fields fall back to
sensible defaults (see ``Config.defaults()``).

File format: YAML.  Two discovery modes are supported and can combine:

  1. Per-run:  a single config passed via ``--config PATH`` on the CLI or
     via the "Config file" field in the GUI.  It applies to every .docx in
     the run.
  2. Per-doc:  next to ``spec.docx`` on disk, the loader automatically
     picks up ``spec.reqx.yaml`` (or ``spec.reqx.yml``) if present.  Keys
     found there OVERRIDE the per-run config for that one document.

Merge semantics
---------------

Merging happens on raw YAML dicts BEFORE materialising a ``Config``
dataclass.  That matters because the dataclass always has default values
for every field — if we merged at dataclass level, an empty per-doc
config would "overwrite" per-run values with their defaults.  Working in
raw-dict space means keys only override when the user actually wrote them
down.

Within the dict, nested mappings merge key-by-key; lists and scalars
replace wholesale.  So a per-doc file that says
``skip_sections: {titles: [Glossary]}`` replaces the per-run list entirely
— it does not append to it.  This is deliberate: list-append semantics
make it impossible to remove entries downstream.

Example config::

    version: 1

    skip_sections:
      titles:
        - Revision History
        - References
        - Glossary
      table_indices: [1]          # 1-based; skip the first top-level table

    tables:
      actor_column: 1             # 1-based index within the row
      content_column: 2
      # Accept alphanumeric section prefixes (SR-1.2, A.1, REQ-042 ...)
      section_prefix: '^\\s*(?:[A-Z]{1,4}[-.]?)?\\d+(?:\\.\\d+)*[.)]?\\s+\\S'
      min_columns: 2
      max_columns: 2

    keywords:
      hard_add:    [is to, are to]
      hard_remove: [will]         # drop noisy future-tense matches
      soft_add:    []
      soft_remove: []

    content:
      skip_if_starts_with:
        - "Note:"
        - "Example:"
        - "See also:"
      skip_pattern: null          # optional regex applied per sentence
      require_primary_actor: false

    parser:
      recursive: true             # walk nested tables of arbitrary depth
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclass schema — used AFTER dict-level merging is complete.
# ---------------------------------------------------------------------------


# Section-prefix recogniser used to tell a "section title" row in the
# 2-column requirements table apart from an "actor" row.  Matches:
#
#   Numeric:        "3.1 ...",  "3.1.2 ...",  "3. ..."
#   Paren-style:    "1) ...",   "3.1) ..."
#   Labelled:       "A.1 ...", "SR-1.2 ...", "REQ-042 ...", "H1.2 ..."
#                   (1–4 uppercase letters, optional '-' or '.' separator)
#   Letter suffix:  "5.1.1a ...", "3.1b) ..."
#                   (single lowercase letter attached to the last digit
#                   group — common in IEEE/ISO subdivisions)
#
# Intentionally does NOT match:
#   Roman numerals ("IV. ...")          — too easily confused with words
#   Labelled keywords ("Section 1 ...") — spelling varies too much
#   Missing whitespace ("3.1Title")     — likely a typo, not a real prefix
#
# If your corpus uses one of the unmatched styles, override
# ``tables.section_prefix`` in a per-run or per-doc YAML config.
DEFAULT_SECTION_PREFIX = (
    r"^\s*(?:[A-Z]{1,4}[-.]?)?\d+(?:\.\d+)*[a-z]?[.)]?\s+\S"
)


@dataclass
class SkipSections:
    titles: List[str] = field(default_factory=list)
    # 1-based indices of top-level tables to ignore entirely.
    table_indices: List[int] = field(default_factory=list)

    def matches_title(self, title: str) -> bool:
        if not title:
            return False
        t = title.strip().lower()
        for raw in self.titles:
            if not raw:
                continue
            r = raw.strip().lower()
            # Match when the section title equals, contains, or starts with
            # the configured skip phrase.  This is forgiving for prefixes
            # like "3. Revision History" or "Annex A — References".
            if r == t or r in t:
                return True
        return False


@dataclass
class TablesConfig:
    actor_column: int = 1                     # 1-based
    content_column: int = 2                   # 1-based
    section_prefix: str = DEFAULT_SECTION_PREFIX
    min_columns: int = 2
    max_columns: int = 2                      # inclusive; set <0 for no cap

    def section_re(self) -> re.Pattern[str]:
        return re.compile(self.section_prefix)

    def is_requirement_table(self, num_columns: int) -> bool:
        if num_columns < self.min_columns:
            return False
        if self.max_columns >= 0 and num_columns > self.max_columns:
            return False
        return True


@dataclass
class KeywordsConfig:
    hard_add: List[str] = field(default_factory=list)
    hard_remove: List[str] = field(default_factory=list)
    soft_add: List[str] = field(default_factory=list)
    soft_remove: List[str] = field(default_factory=list)


@dataclass
class ContentConfig:
    skip_if_starts_with: List[str] = field(default_factory=list)
    skip_pattern: Optional[str] = None
    # When true, candidate sentences with no primary actor are dropped.
    # Handy for very noisy preamble prose.
    require_primary_actor: bool = False

    def skip_pattern_re(self) -> Optional[re.Pattern[str]]:
        if not self.skip_pattern:
            return None
        return re.compile(self.skip_pattern, flags=re.IGNORECASE)

    def should_skip(self, text: str) -> bool:
        if not text:
            return True
        stripped = text.strip()
        for prefix in self.skip_if_starts_with:
            if prefix and stripped.lower().startswith(prefix.strip().lower()):
                return True
        pat = self.skip_pattern_re()
        if pat is not None and pat.search(stripped):
            return True
        return False


@dataclass
class ParserConfig:
    # When True the parser walks cells and nested tables recursively to
    # arbitrary depth.  When False it keeps the legacy one-level-of-nesting
    # behaviour.
    recursive: bool = True


@dataclass
class Config:
    version: int = 1
    skip_sections: SkipSections = field(default_factory=SkipSections)
    tables: TablesConfig = field(default_factory=TablesConfig)
    keywords: KeywordsConfig = field(default_factory=KeywordsConfig)
    content: ContentConfig = field(default_factory=ContentConfig)
    parser: ParserConfig = field(default_factory=ParserConfig)

    # Human-readable origin (file path or "default") — useful for logs.
    source: str = "default"

    @classmethod
    def defaults(cls) -> "Config":
        return cls()


# ---------------------------------------------------------------------------
# Raw-dict API — load, validate, merge.
# ---------------------------------------------------------------------------


_TOP_LEVEL_SECTIONS = {
    "skip_sections": SkipSections,
    "tables": TablesConfig,
    "keywords": KeywordsConfig,
    "content": ContentConfig,
    "parser": ParserConfig,
}
_ALLOWED_TOP_LEVEL_KEYS = set(_TOP_LEVEL_SECTIONS) | {"version"}


def load_config_raw(path: Path) -> Dict[str, Any]:
    """Load a YAML file as a raw dict, validating top-level + section keys.

    Raises ``FileNotFoundError`` / ``ValueError`` / ``ImportError`` with
    friendly messages.  Does not instantiate the ``Config`` dataclass —
    that happens after all raw sources are merged.
    """
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required to load config files.  "
            "Install with:  pip install pyyaml"
        ) from exc

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    if not isinstance(raw, dict):
        raise ValueError(
            f"{path.name}: config root must be a mapping "
            f"(got {type(raw).__name__})."
        )
    _validate_raw(raw, origin=str(path))
    return raw


def _validate_raw(raw: Dict[str, Any], *, origin: str) -> None:
    """Reject unknown top-level or per-section keys early with a clear error."""
    unknown = set(raw.keys()) - _ALLOWED_TOP_LEVEL_KEYS
    if unknown:
        raise ValueError(
            f"{origin}: unknown top-level keys: {sorted(unknown)}.  "
            f"Allowed: {sorted(_ALLOWED_TOP_LEVEL_KEYS)}."
        )
    for key, cls in _TOP_LEVEL_SECTIONS.items():
        if key not in raw or raw[key] is None:
            continue
        sub = raw[key]
        if not isinstance(sub, dict):
            raise ValueError(
                f"{origin}: key '{key}' must be a mapping "
                f"(got {type(sub).__name__})."
            )
        allowed_fields = {
            f.name for f in cls.__dataclass_fields__.values()  # type: ignore[attr-defined]
        }
        sub_unknown = set(sub.keys()) - allowed_fields
        if sub_unknown:
            raise ValueError(
                f"{origin}: unknown keys under '{key}': {sorted(sub_unknown)}.  "
                f"Allowed: {sorted(allowed_fields)}."
            )


def merge_raw(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge two raw-dict configs.  Override wins on conflicts.

    Nested mappings merge key-by-key.  Lists and scalars replace wholesale.
    """
    result: Dict[str, Any] = dict(base)
    for key, over_val in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(over_val, dict)
        ):
            result[key] = merge_raw(result[key], over_val)
        else:
            result[key] = over_val
    return result


def build_config(raw: Optional[Dict[str, Any]] = None, *, source: str = "default") -> Config:
    """Materialise a Config from a raw dict (keys missing -> dataclass defaults).

    Pass ``raw=None`` (or ``{}``) to get pure defaults.
    """
    raw = raw or {}
    kwargs: Dict[str, Any] = {"source": source}
    if "version" in raw:
        kwargs["version"] = int(raw["version"])
    for key, cls in _TOP_LEVEL_SECTIONS.items():
        if key in raw and raw[key] is not None:
            kwargs[key] = cls(**raw[key])
    return Config(**kwargs)


# ---------------------------------------------------------------------------
# High-level helpers — these compose load + merge + build.
# ---------------------------------------------------------------------------


def autodiscover_config(docx_path: Path) -> Optional[Path]:
    """Return the path to ``<stem>.reqx.(yaml|yml)`` next to a .docx, or None."""
    docx_path = Path(docx_path)
    folder = docx_path.parent
    stem = docx_path.stem
    for ext in (".reqx.yaml", ".reqx.yml"):
        candidate = folder / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def resolve_config(
    run_config_path: Optional[Path] = None,
    docx_path: Optional[Path] = None,
    keywords_path: Optional[Path] = None,
) -> Config:
    """Build a Config for one document.

    Layers (each one overrides the one above):
      1. Dataclass defaults.
      2. Per-run config (``run_config_path``), if given.
      3. Standalone keywords file (``keywords_path``), if given — a small
         YAML with just the keyword knobs.  See :func:`load_keywords_raw`.
         Overrides the ``keywords:`` section of the per-run config only.
      4. Per-doc config (``<docstem>.reqx.yaml`` next to ``docx_path``),
         if it exists — can override anything above.

    Returns a Config with ``source`` set to a ``+``-joined list of paths
    that actually contributed.
    """
    layers_raw: List[Dict[str, Any]] = []
    origins: List[str] = []

    if run_config_path is not None:
        raw = load_config_raw(Path(run_config_path))
        layers_raw.append(raw)
        origins.append(str(run_config_path))

    if keywords_path is not None:
        kw_raw = load_keywords_raw(Path(keywords_path))
        layers_raw.append({"keywords": kw_raw})
        origins.append(f"keywords:{Path(keywords_path).name}")

    if docx_path is not None:
        per_doc = autodiscover_config(Path(docx_path))
        if per_doc is not None:
            raw = load_config_raw(per_doc)
            layers_raw.append(raw)
            origins.append(str(per_doc))

    merged: Dict[str, Any] = {}
    for layer in layers_raw:
        merged = merge_raw(merged, layer)

    source = " + ".join(origins) if origins else "default"
    return build_config(merged, source=source)


# ---------------------------------------------------------------------------
# Standalone keywords file — a smaller, purpose-built surface so non-technical
# users can tune just the keyword lists without learning the full config
# schema.  Can be combined with a full --config.
# ---------------------------------------------------------------------------


#: Field names allowed in a standalone keywords file.  ``hard`` / ``soft``
#: REPLACE the built-in list for that bucket; the ``*_add`` / ``*_remove``
#: variants tweak the built-in list.  Mixing ``hard`` and ``hard_add`` in
#: the same file is rejected — they contradict each other.
_KEYWORDS_FIELDS = frozenset({
    "hard", "soft",
    "hard_add", "hard_remove", "soft_add", "soft_remove",
})


def load_keywords_raw(path: Path) -> Dict[str, Any]:
    """Load a standalone keywords YAML and return a ``keywords:``-shaped dict.

    Supported schemas (both YAML, both optional at the field level):

    1. **Replace** — wholesale replacement of a bucket::

           hard: [shall, must, is to]
           soft: [should, may]

       The built-in lists for ``hard`` / ``soft`` are discarded and only
       the listed words count.  Empty list means "nothing in this bucket".

    2. **Tweak** — keep built-ins, then add/remove::

           hard_add:    [is to, are to]
           hard_remove: [will]
           soft_add:    []
           soft_remove: []

       Equivalent to writing the same keys under ``keywords:`` in a
       regular ``--config`` file.

    Shapes can be combined across buckets (``hard: ...`` + ``soft_add: ...``)
    but cannot be combined *within* a bucket (``hard`` + ``hard_add``).

    Accepts both ``.yaml`` / ``.yml`` and ``.txt`` extensions — the
    ``.txt`` path treats each non-blank, non-comment line as a ``hard``
    keyword, section-marker lines (``[hard]`` / ``[soft]`` /
    ``[hard_remove]`` …) flip the current bucket.  Good for one-liner
    tweaks without reaching for YAML syntax.

    Raises ``FileNotFoundError`` / ``ValueError`` on problems — caller
    is expected to surface these to the user.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Keywords file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "PyYAML is required to load YAML keywords files.  "
                "Install with:  pip install pyyaml"
            ) from exc
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        if not isinstance(raw, dict):
            raise ValueError(
                f"{path.name}: keywords file root must be a mapping "
                f"(got {type(raw).__name__})."
            )
    elif suffix in {".txt", ".kw", ""}:
        raw = _parse_keywords_txt(path)
    else:
        raise ValueError(
            f"{path.name}: unsupported keywords file extension '{suffix}'. "
            f"Use .yaml, .yml, .txt, or .kw."
        )

    unknown = set(raw.keys()) - _KEYWORDS_FIELDS
    if unknown:
        raise ValueError(
            f"{path.name}: unknown keys {sorted(unknown)}.  "
            f"Allowed: {sorted(_KEYWORDS_FIELDS)}."
        )

    # Each value must be a list (if present).
    for key, val in list(raw.items()):
        if val is None:
            raw[key] = []
            continue
        if not isinstance(val, list):
            raise ValueError(
                f"{path.name}: key '{key}' must be a list of strings "
                f"(got {type(val).__name__})."
            )
        raw[key] = [str(x).strip() for x in val if str(x).strip()]

    # "hard" + "hard_add" / "hard_remove" in the same file is an obvious
    # user mistake — the two shapes contradict each other.  Catch early.
    for bucket in ("hard", "soft"):
        if bucket in raw and (f"{bucket}_add" in raw or f"{bucket}_remove" in raw):
            raise ValueError(
                f"{path.name}: '{bucket}' replaces the bucket entirely — "
                f"don't combine it with '{bucket}_add' / '{bucket}_remove' "
                f"in the same file."
            )

    # Translate "replace" shape into add/remove shape the rest of the
    # pipeline already understands.  For "hard: [X, Y]" we emit:
    #     hard_remove = baseline_hard  (caller applies: "drop all builtins")
    #     hard_add    = [X, Y]
    # We express "drop everything built-in" with a special sentinel: the
    # string "*".  KeywordsConfig / KeywordMatcher are taught to honour it.
    result: Dict[str, Any] = {
        "hard_add": list(raw.get("hard_add", [])),
        "hard_remove": list(raw.get("hard_remove", [])),
        "soft_add": list(raw.get("soft_add", [])),
        "soft_remove": list(raw.get("soft_remove", [])),
    }
    if "hard" in raw:
        result["hard_remove"] = ["*"]
        result["hard_add"] = list(raw["hard"])
    if "soft" in raw:
        result["soft_remove"] = ["*"]
        result["soft_add"] = list(raw["soft"])

    return result


def _parse_keywords_txt(path: Path) -> Dict[str, List[str]]:
    """Minimal text-format parser for one-liner keyword tweaks.

    Format::

        # comments start with '#'
        [hard_add]
        is to
        are to

        [hard_remove]
        will

        [soft_add]
        recommended

    Lines before any section marker are treated as ``hard_add`` entries.
    Unknown sections raise ``ValueError``.
    """
    buckets: Dict[str, List[str]] = {}
    current = "hard_add"
    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip().lower()
                if section not in _KEYWORDS_FIELDS:
                    raise ValueError(
                        f"{path.name}: unknown section '[{section}]'.  "
                        f"Allowed: {sorted(_KEYWORDS_FIELDS)}."
                    )
                current = section
                buckets.setdefault(current, [])
                continue
            buckets.setdefault(current, []).append(line)
    return buckets
