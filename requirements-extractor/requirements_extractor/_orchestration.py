"""Shared orchestration helpers for the per-mode runners.

``extract_from_files`` (the requirements-mode runner in ``extractor.py``)
and ``scan_actors_from_files`` (the actors-mode runner in
``actor_scan.py``) historically both carried ~80 lines of identical
setup boilerplate at the top: load the optional actors file, init an
``ActorResolver`` (with the same NLP-unavailable warning), validate
the per-run config + keywords paths up front so typos surface before
parsing, and resolve a per-doc config for each input file.  Two
copies meant any narrowing of an exception filter, any tweak to a
log line, or any reorder had to be applied twice — and getting it
wrong meant one mode silently behaved differently from the other.

This module collects those shared steps as small, side-effect-honest
helpers.  Each helper:

* takes the user-supplied path / option,
* takes a ``stats`` object satisfying :class:`HasErrors` (so it can
  record a structured warning),
* takes a ``log`` callable (so it can mirror the warning to whatever
  observer the caller wired up — usually CLI stdout or the GUI log),
* returns the loaded resource on success, or a sensible fallback
  (``[]``, ``None``, ``Config.defaults()``) on failure.

Per-file iteration (cancel + progress + suffix gate) is split between
two helpers: :func:`should_skip_input` for the suffix gate (which
varies between modes — requirements accepts .docx/.doc/.pdf, actors
accepts only .docx) and the cancel/progress loop itself stays inline
in each runner because it needs to raise a mode-specific exception
(:class:`ExtractionCancelled` vs :class:`ActorScanCancelled`).  Both
runners depend on this module; this module depends on nothing in
either runner — keeps the dependency graph one-way.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, Protocol, Sequence, Set, Tuple

from .actors import ActorEntry, ActorResolver, load_actors_from_xlsx
from .config import Config, resolve_config


class HasErrors(Protocol):
    """Structural type for any stats object with an ``errors`` list.

    ``ExtractionStats`` and ``ActorScanStats`` both satisfy this without
    having to share a base class — the helpers here only need to
    ``.append`` a string, nothing else.
    """

    errors: List[str]


# ---------------------------------------------------------------------------
# Actors + resolver
# ---------------------------------------------------------------------------


def load_actors_or_warn(
    actors_xlsx: Optional[Path],
    stats: HasErrors,
    log: Callable[[str], None],
    *,
    label: str = "actors",
) -> List[ActorEntry]:
    """Load an optional actors xlsx; record a friendly warning on failure.

    ``label`` lets each caller pick the words shown on the success line:
    requirements mode says ``"actors"``, actors-mode (where the file is a
    seed for the harvest pass) says ``"seed actors"``.  Returns ``[]``
    when the path is None or the load fails — both runners then proceed
    without an actors list.

    Exceptions narrowed to (OSError, ValueError, KeyError) — same set
    as the original inline code:

    * **OSError** — file missing / permission denied / file locked.
    * **ValueError** — bad header in the workbook (the loader's own
      validation surfaces this).
    * **KeyError** — a header is present but a required cell is empty,
      which openpyxl propagates as KeyError on row access.
    """
    if actors_xlsx is None:
        return []
    try:
        actors = load_actors_from_xlsx(Path(actors_xlsx))
        log(f"Loaded {len(actors)} {label} from {Path(actors_xlsx).name}.")
        return actors
    except (OSError, ValueError, KeyError) as e:
        # Match the historical phrasing — different per mode so users
        # who scrape logs aren't surprised.
        prefix = "seed actors" if label == "seed actors" else "actors file"
        stats.errors.append(f"Failed to load {prefix}: {e}")
        log(f"WARNING: {stats.errors[-1]}")
        return []


def build_resolver(
    actors: Sequence[ActorEntry],
    use_nlp: bool,
    stats: HasErrors,
    log: Callable[[str], None],
) -> ActorResolver:
    """Build the ``ActorResolver`` and warn if NLP was asked for but missing.

    Both modes tolerate "NLP requested but unavailable" — the resolver
    silently degrades to the regex path.  We surface it as a warning
    rather than an error because the run can still produce useful
    output; the user just won't get NER-driven secondary actors.
    """
    resolver = ActorResolver(actors=actors, use_nlp=use_nlp)
    if use_nlp and not resolver.has_nlp():
        stats.errors.append(
            "NLP requested but spaCy (with an English model) is not available. "
            "Install with:  pip install spacy  &&  python -m spacy download en_core_web_sm"
        )
        log(f"WARNING: {stats.errors[-1]}")
    return resolver


# ---------------------------------------------------------------------------
# Run-config validation (per-run YAML + standalone keywords file)
# ---------------------------------------------------------------------------


def validate_run_config(
    config_path: Optional[Path],
    keywords_path: Optional[Path],
    stats: HasErrors,
    log: Callable[[str], None],
) -> Tuple[Optional[Path], Optional[Path]]:
    """Validate the per-run YAML config + standalone keywords file up front.

    Catches typos before any document is parsed.  Returns the (possibly
    cleared) ``(run_config_path, run_keywords_path)`` pair so the caller
    can pass them to per-doc :func:`resolve_config` calls without having
    to also remember to drop a path that just failed validation.

    Match the historical ordering: if both are provided we run a single
    ``resolve_config`` to validate them together (they layer); if only
    keywords is provided we still validate it via ``resolve_config`` so
    a broken keywords file fails fast.

    Exception narrowing:

    * **OSError** — file not found / permission denied.
    * **ValueError** — YAML parse error or schema-validation error in
      :mod:`config`.
    * **ImportError** — PyYAML missing for a ``.yaml`` file.
    """
    run_config_path: Optional[Path] = Path(config_path) if config_path else None
    run_keywords_path: Optional[Path] = (
        Path(keywords_path) if keywords_path else None
    )

    if run_config_path is not None:
        try:
            resolve_config(
                run_config_path=run_config_path,
                docx_path=None,
                keywords_path=run_keywords_path,
            )
            log(f"Loaded run config: {run_config_path.name}")
        except (OSError, ValueError, ImportError) as e:
            stats.errors.append(f"Failed to load config {run_config_path}: {e}")
            log(f"WARNING: {stats.errors[-1]}")
            run_config_path = None
        return run_config_path, run_keywords_path

    if run_keywords_path is not None:
        try:
            resolve_config(
                run_config_path=None,
                docx_path=None,
                keywords_path=run_keywords_path,
            )
            log(f"Loaded keywords file: {run_keywords_path.name}")
        except (OSError, ValueError, ImportError) as e:
            stats.errors.append(
                f"Failed to load keywords file {run_keywords_path}: {e}"
            )
            log(f"WARNING: {stats.errors[-1]}")
            run_keywords_path = None

    return run_config_path, run_keywords_path


def resolve_per_doc_config(
    path: Path,
    run_config_path: Optional[Path],
    run_keywords_path: Optional[Path],
    stats: HasErrors,
    log: Callable[[str], None],
) -> Config:
    """Resolve the per-document config (with auto-discovered overrides).

    A ``<docstem>.reqx.yaml`` next to the document gets layered on top
    of the per-run config for that single file.  See
    :mod:`requirements_extractor.config` for the merge rules.

    Falls back to ``Config.defaults()`` (with a warning recorded) when
    a per-doc config exists but is malformed — keeps the per-file loop
    going on the assumption that one bad config shouldn't kill a batch.
    """
    try:
        return resolve_config(
            run_config_path=run_config_path,
            docx_path=path,
            keywords_path=run_keywords_path,
        )
    except (OSError, ValueError, ImportError) as e:
        stats.errors.append(
            f"Failed to load per-doc config for {path.name}: {e}"
        )
        log(f"WARNING: {stats.errors[-1]}")
        return Config.defaults()


# ---------------------------------------------------------------------------
# Per-file path validation
# ---------------------------------------------------------------------------


def validate_input_path(
    path: Path,
    accepted_suffixes: Set[str],
    stats: HasErrors,
    log: Callable[[str], None],
    *,
    unsupported_message: Optional[Callable[[Path], str]] = None,
) -> Optional[Path]:
    """Return the path if it's a usable input, else log + return None.

    Two checks: the file exists, and its lower-case suffix is in
    ``accepted_suffixes`` (e.g. ``{".docx", ".doc", ".pdf"}`` for
    requirements mode, ``{".docx"}`` for actors mode).  Both failures
    record a structured warning on ``stats.errors`` and emit the same
    line through ``log``; the caller's per-file loop should ``continue``
    on a None return.

    ``unsupported_message`` lets the caller plug in mode-specific phrasing
    for the suffix-mismatch case.  Defaults to a generic message that
    spells out the accepted suffixes — fine for new callers, but the
    two existing callers pass their historical phrasing verbatim so
    saved logs don't shift wording.
    """
    if not path.exists():
        stats.errors.append(f"File not found: {path}")
        log(f"WARNING: {stats.errors[-1]}")
        return None

    suffix = path.suffix.lower()
    if suffix not in accepted_suffixes:
        if unsupported_message is not None:
            stats.errors.append(unsupported_message(path))
        else:
            allowed = ", ".join(sorted(accepted_suffixes))
            stats.errors.append(
                f"Skipping unsupported file: {path.name} "
                f"(expected one of {allowed})"
            )
        log(f"WARNING: {stats.errors[-1]}")
        return None

    return path
