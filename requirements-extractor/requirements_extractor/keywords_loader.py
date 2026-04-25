"""Standalone keywords-file loader.

The ``--keywords PATH`` flag (CLI) and the matching GUI field accept a
small file that tunes just the HARD/SOFT keyword buckets without
forcing the user to author a full ``--config``.  This module is the
loader for that file format.

Two surface shapes are supported:

* **Replace** — wholesale replacement of a bucket::

      hard: [shall, must, is to]
      soft: [should, may]

  The built-in lists for ``hard`` / ``soft`` are discarded and only
  the listed words count.  Empty list means "nothing in this bucket".

* **Tweak** — keep built-ins, then add/remove::

      hard_add:    [is to, are to]
      hard_remove: [will]
      soft_add:    []
      soft_remove: []

  Equivalent to writing the same keys under ``keywords:`` in a regular
  ``--config`` file.

Shapes can be combined across buckets (``hard: …`` + ``soft_add: …``)
but cannot be combined *within* a bucket (``hard`` + ``hard_add``) —
the two are contradictory and we reject early with a clear error.

Two file formats are supported:

* **YAML** — extension ``.yaml`` / ``.yml``.  Standard mapping shape
  matching the schema above.  Requires PyYAML installed at the call
  site.
* **Text** — extension ``.txt`` / ``.kw`` (or no extension).  One
  keyword per line, ``# comments`` ignored, optional ``[bucket]``
  markers (``[hard]`` / ``[soft]`` / ``[hard_add]`` / ``[hard_remove]``
  / ``[soft_add]`` / ``[soft_remove]``) flip the current bucket.
  Lines before any marker are treated as ``hard_add`` entries.

This module was extracted from ``config.py`` (which had grown to
~600 lines bundling schema, validation, YAML loading, AND keyword
loading).  The keyword loaders are pure functions with their own
test coverage in ``test_batch_improvements.py``; pulling them into
their own module keeps ``config.py`` focused on the schema-of-truth
role.

``config.load_keywords_raw`` is preserved as a re-export from this
module so existing callers (CLI, GUI, tests) don't need to change
their imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


#: Allowed top-level keys in a standalone keywords file.
#:
#: ``hard`` / ``soft`` are the "replace" shape; ``*_add`` / ``*_remove``
#: are the "tweak" shape.  Mixing ``hard`` with ``hard_add`` /
#: ``hard_remove`` in the same file is rejected — they contradict each
#: other.  See module docstring for the full explanation of each shape.
KEYWORDS_FIELDS = frozenset({
    "hard", "soft",
    "hard_add", "hard_remove", "soft_add", "soft_remove",
})


def load_keywords_raw(path: Path) -> Dict[str, Any]:
    """Load a standalone keywords file and return a ``keywords:``-shaped dict.

    Returns the *normalised* shape — i.e. always populated with all four
    ``*_add`` / ``*_remove`` keys, with the "replace" shape translated
    into the "tweak" shape via the ``"*"`` sentinel in the corresponding
    ``*_remove`` list (which the downstream :class:`KeywordsConfig` /
    :class:`KeywordMatcher` interpret as "drop every built-in baseline
    entry for this bucket").  This means callers don't have to handle
    both shapes — they just see a uniform dict.

    Raises:

    * ``FileNotFoundError`` — path doesn't exist.
    * ``ValueError`` — file structure is wrong (root not a mapping,
      unknown key, value not a list, replace+tweak combined within a
      bucket, unknown ``[section]`` marker in text format).
    * ``ImportError`` — PyYAML is required for ``.yaml`` / ``.yml``
      files but isn't installed.
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
        raw = _parse_text_format(path)
    else:
        raise ValueError(
            f"{path.name}: unsupported keywords file extension '{suffix}'. "
            f"Use .yaml, .yml, .txt, or .kw."
        )

    unknown = set(raw.keys()) - KEYWORDS_FIELDS
    if unknown:
        raise ValueError(
            f"{path.name}: unknown keys {sorted(unknown)}.  "
            f"Allowed: {sorted(KEYWORDS_FIELDS)}."
        )

    # Normalise every present value to a clean string-list.
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
    # user mistake — the two shapes contradict each other.  Catch early
    # so the user sees a friendly error instead of a confusing partial
    # bucket replacement at runtime.
    for bucket in ("hard", "soft"):
        if bucket in raw and (f"{bucket}_add" in raw or f"{bucket}_remove" in raw):
            raise ValueError(
                f"{path.name}: '{bucket}' replaces the bucket entirely — "
                f"don't combine it with '{bucket}_add' / '{bucket}_remove' "
                f"in the same file."
            )

    # Translate the "replace" shape into the "tweak" shape the rest of
    # the pipeline already understands.  For "hard: [X, Y]" we emit:
    #     hard_remove = ["*"]   (caller applies: "drop every built-in")
    #     hard_add    = [X, Y]
    # The "*" sentinel in the *_remove list tells KeywordsConfig /
    # KeywordMatcher to clear the baseline before applying the additions.
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


def _parse_text_format(path: Path) -> Dict[str, List[str]]:
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
                if section not in KEYWORDS_FIELDS:
                    raise ValueError(
                        f"{path.name}: unknown section '[{section}]'.  "
                        f"Allowed: {sorted(KEYWORDS_FIELDS)}."
                    )
                current = section
                buckets.setdefault(current, [])
                continue
            buckets.setdefault(current, []).append(line)
    return buckets
