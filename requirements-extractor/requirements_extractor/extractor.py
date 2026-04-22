"""High-level orchestrator — put all pieces together."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from .actors import ActorResolver, load_actors_from_xlsx
from .config import Config, resolve_config
from .models import ExtractionStats, Requirement, RequirementEvent
from .parser import parse_docx_events
from .statement_set import write_statement_set
from .writer import write_requirements


@dataclass
class ExtractionResult:
    requirements: List[Requirement]
    stats: ExtractionStats
    output_path: Optional[Path] = None
    statement_set_path: Optional[Path] = None


class ExtractionCancelled(RuntimeError):
    """Raised internally when ``cancel_check`` returns True.

    The GUI catches this to distinguish 'user pressed Cancel' from a
    real error.  CLI callers should normally treat it the same as a
    successful partial run — the workbook up to the cancellation point
    is *not* written, to avoid leaving a half-finished artifact on disk.
    """


def extract_from_files(
    input_paths: Sequence[Path],
    output_path: Path,
    *,
    actors_xlsx: Optional[Path] = None,
    use_nlp: bool = False,
    statement_set_path: Optional[Path] = None,
    config_path: Optional[Path] = None,
    progress: Optional[Callable[[str], None]] = None,
    file_progress: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> ExtractionResult:
    """Parse every .docx in `input_paths` and write results.

    Always writes the Excel workbook at `output_path` (unless cancelled).
    If `statement_set_path` is provided, additionally writes a
    statement-set CSV in the hierarchical (Level N, Description N) format.

    `config_path` points to a per-run YAML config.  Any ``<stem>.reqx.yaml``
    sitting next to an input .docx is also auto-discovered and layered on
    top of the per-run config for that single file (see
    ``requirements_extractor.config`` for details).

    ``file_progress(i, n, name)`` is called once at the start of each
    file (``i`` is 1-based, ``n`` is total input count).  The GUI uses
    it to drive a determinate progress bar.

    ``cancel_check()`` is polled before each file.  If it returns True
    the run aborts and :class:`ExtractionCancelled` is raised before any
    output is written.
    """

    stats = ExtractionStats()
    log = progress or (lambda msg: None)

    actors = []
    if actors_xlsx is not None:
        try:
            actors = load_actors_from_xlsx(Path(actors_xlsx))
            log(f"Loaded {len(actors)} actors from {Path(actors_xlsx).name}.")
        except Exception as e:  # noqa: BLE001
            stats.errors.append(f"Failed to load actors file: {e}")
            log(f"WARNING: {stats.errors[-1]}")

    resolver = ActorResolver(actors=actors, use_nlp=use_nlp)
    if use_nlp and resolver._nlp is None:
        stats.errors.append(
            "NLP requested but spaCy (with an English model) is not available. "
            "Install with:  pip install spacy  &&  python -m spacy download en_core_web_sm"
        )
        log(f"WARNING: {stats.errors[-1]}")

    # Validate the per-run config once up front so typos surface before we
    # parse any documents.  (Per-doc overrides are loaded lazily below.)
    run_config_path: Optional[Path] = Path(config_path) if config_path else None
    if run_config_path is not None:
        try:
            resolve_config(run_config_path=run_config_path, docx_path=None)
            log(f"Loaded run config: {run_config_path.name}")
        except Exception as e:  # noqa: BLE001
            stats.errors.append(f"Failed to load config {run_config_path}: {e}")
            log(f"WARNING: {stats.errors[-1]}")
            run_config_path = None

    all_reqs: List[Requirement] = []
    events_per_file: List[Tuple[str, List[object]]] = []

    input_list = list(input_paths)
    total_inputs = len(input_list)

    for idx, path in enumerate(input_list, start=1):
        if cancel_check is not None and cancel_check():
            log(f"Cancelled by user after {idx - 1}/{total_inputs} file(s).")
            raise ExtractionCancelled(
                f"Cancelled after {idx - 1}/{total_inputs} file(s)."
            )
        if file_progress is not None:
            file_progress(idx, total_inputs, Path(path).name)
        path = Path(path)
        if not path.exists():
            stats.errors.append(f"File not found: {path}")
            log(f"WARNING: {stats.errors[-1]}")
            continue
        if path.suffix.lower() != ".docx":
            stats.errors.append(f"Skipping non-.docx file: {path.name}")
            log(f"WARNING: {stats.errors[-1]}")
            continue

        # Per-doc config discovery happens here so each file can override.
        try:
            cfg: Config = resolve_config(
                run_config_path=run_config_path, docx_path=path,
            )
        except Exception as e:  # noqa: BLE001
            stats.errors.append(
                f"Failed to load per-doc config for {path.name}: {e}"
            )
            log(f"WARNING: {stats.errors[-1]}")
            cfg = Config.defaults()

        log(f"Parsing {path.name} (config: {cfg.source}) ...")
        try:
            events = parse_docx_events(
                path, resolver_fn=resolver.resolve, config=cfg,
            )
        except Exception as e:  # noqa: BLE001
            stats.errors.append(f"Error parsing {path.name}: {e}")
            log(f"ERROR: {stats.errors[-1]}")
            continue

        events_per_file.append((path.name, events))

        file_reqs = [e.requirement for e in events if isinstance(e, RequirementEvent)]
        # Re-number within the combined output so 'Order' is 1..N overall.
        for r in file_reqs:
            r.order = len(all_reqs) + 1
            all_reqs.append(r)
        stats.files_processed += 1
        log(f"  found {len(file_reqs)} requirement candidates.")

    stats.requirements_found = len(all_reqs)
    stats.hard_count = sum(1 for r in all_reqs if r.req_type == "Hard")
    stats.soft_count = sum(1 for r in all_reqs if r.req_type == "Soft")

    output_path = Path(output_path)
    write_requirements(all_reqs, output_path)
    log(f"Wrote {len(all_reqs)} rows to {output_path}.")

    stmt_path: Optional[Path] = None
    if statement_set_path is not None:
        stmt_path = Path(statement_set_path)
        write_statement_set(events_per_file, stmt_path)
        log(f"Wrote statement-set CSV to {stmt_path}.")

    return ExtractionResult(
        requirements=all_reqs,
        stats=stats,
        output_path=output_path,
        statement_set_path=stmt_path,
    )
