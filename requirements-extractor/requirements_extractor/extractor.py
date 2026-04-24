"""High-level orchestrator — put all pieces together."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ._logging import make_progress_logger
from ._orchestration import (
    build_resolver,
    load_actors_or_warn,
    resolve_per_doc_config,
    validate_input_path,
    validate_run_config,
)
from .config import Config
from .models import (
    ExtractionStats,
    Requirement,
    RequirementEvent,
    annotate_cross_source_duplicates,
    ensure_unique_stable_ids,
)
from .legacy_formats import (
    LibreOfficeUnavailable,
    PdfSupportUnavailable,
    prepare_for_parser,
)
from .parser import parse_docx_events
from .statement_set import write_statement_set
from .writer import write_requirements
from .reqif_writer import (
    SUPPORTED_DIALECTS as REQIF_SUPPORTED_DIALECTS,
    write_requirements_reqif,
)
from .writers_extra import write_requirements_json, write_requirements_md


#: Supported extra-format labels for ``extract_from_files(emit_extra=...)``.
#: Kept alongside the two writers so new formats only need one place to
#: register.  ReqIF's dialect is controlled by the ``reqif_dialect``
#: kwarg, not by format name — keeps the output extension as ``.reqif``
#: regardless of dialect.
EXTRA_FORMAT_WRITERS = {
    "json": write_requirements_json,
    "md": write_requirements_md,
    "reqif": write_requirements_reqif,
}


@dataclass
class ExtractionResult:
    requirements: List[Requirement]
    stats: ExtractionStats
    output_path: Optional[Path] = None
    statement_set_path: Optional[Path] = None
    dry_run: bool = False
    #: Extra format → written path.  Populated when the caller passes
    #: ``emit_extra`` to :func:`extract_from_files`.  Empty dict when
    #: only the default xlsx was emitted.
    extra_output_paths: Dict[str, Path] = field(default_factory=dict)


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
    keywords_path: Optional[Path] = None,
    progress: Optional[Callable[[str], None]] = None,
    file_progress: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    dry_run: bool = False,
    emit_extra: Optional[Sequence[str]] = None,
    reqif_dialect: str = "basic",
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

    ``dry_run=True`` runs the full parse pipeline (including stable-ID
    assignment) but skips both the Excel and statement-set writes.  The
    returned :class:`ExtractionResult` still contains the in-memory
    requirements list so callers can display counts or sample rows.  The
    ``output_path`` / ``statement_set_path`` fields on the result are
    left as ``None`` in a dry run to make "no file was created" obvious.
    """

    stats = ExtractionStats()
    log = make_progress_logger(progress)

    actors = load_actors_or_warn(actors_xlsx, stats, log, label="actors")
    resolver = build_resolver(actors, use_nlp, stats, log)

    # Validate the per-run config once up front so typos surface before we
    # parse any documents.  (Per-doc overrides are loaded lazily below.)
    run_config_path, run_keywords_path = validate_run_config(
        config_path, keywords_path, stats, log,
    )

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
        validated = validate_input_path(
            path,
            {".docx", ".doc", ".pdf"},
            stats,
            log,
            unsupported_message=lambda p: (
                f"Skipping unsupported file: {p.name} "
                f"(expected .docx, .doc, or .pdf)"
            ),
        )
        if validated is None:
            continue
        path = validated

        # Per-doc config discovery happens here so each file can override.
        # We pass the original path so ``<stem>.reqx.yaml`` lookups work
        # against the authored document regardless of whether we'll
        # actually parse a converted temp copy below.
        cfg: Config = resolve_per_doc_config(
            path, run_config_path, run_keywords_path, stats, log,
        )

        log(f"Parsing {path.name} (config: {cfg.source}) ...")
        try:
            # Legacy-format routing: .doc and .pdf get converted to a
            # temp .docx via ``prepare_for_parser``.  .docx files go
            # through unchanged (no tempdir allocated).  The context
            # manager owns cleanup on both the success and error paths.
            with prepare_for_parser(path) as ready_path:
                events = parse_docx_events(
                    ready_path, resolver_fn=resolver.resolve, config=cfg,
                )
            # Re-stamp source_file on every emitted requirement so the
            # output reports the original input name (``spec.doc`` /
            # ``spec.pdf``) rather than the tempdir path the parser
            # actually read.
            if path.suffix.lower() != ".docx":
                for ev in events:
                    if isinstance(ev, RequirementEvent):
                        ev.requirement.source_file = path.name
        except LibreOfficeUnavailable as e:
            stats.errors.append(
                f"Cannot read {path.name}: {e}"
            )
            log(f"WARNING: {stats.errors[-1]}")
            continue
        except PdfSupportUnavailable as e:
            stats.errors.append(
                f"Cannot read {path.name}: {e}"
            )
            log(f"WARNING: {stats.errors[-1]}")
            continue
        except Exception as e:  # noqa: BLE001 — per-file: keep going on next doc
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

    # Assign unique stable IDs before any writer sees the list so every
    # output consumer gets the same values.  Duplicate (file, actor, text)
    # rows get ``-1``/``-2`` suffixes in first-seen order.
    ensure_unique_stable_ids(all_reqs)

    # Cross-source dedup — flag later occurrences of the same
    # (actor, text) pair with a "Duplicate of …" note.  Intra-file
    # duplicates are already handled by the stable-ID suffixing above;
    # this pass catches the common "boilerplate shared across specs"
    # case (REVIEW §1.10) where two files have byte-identical rows.
    dup_count = annotate_cross_source_duplicates(all_reqs)
    if dup_count:
        log(f"Flagged {dup_count} cross-source duplicate row(s).")

    if dry_run:
        log(f"Dry run: parsed {len(all_reqs)} requirements; no files written.")
        return ExtractionResult(
            requirements=all_reqs,
            stats=stats,
            output_path=None,
            statement_set_path=None,
            dry_run=True,
        )

    output_path = Path(output_path)
    write_requirements(all_reqs, output_path)
    log(f"Wrote {len(all_reqs)} rows to {output_path}.")

    stmt_path: Optional[Path] = None
    if statement_set_path is not None:
        stmt_path = Path(statement_set_path)
        write_statement_set(events_per_file, stmt_path)
        log(f"Wrote statement-set CSV to {stmt_path}.")

    # Optional extra-format emissions (JSON, Markdown, ReqIF).  Each
    # extra format lands alongside the xlsx at ``<stem>.<ext>``.
    # Unknown format labels produce a warning but don't abort the run.
    # ReqIF uses ``reqif_dialect`` to pick a flavour (basic / cameo /
    # doors); see :mod:`reqif_writer` for the dialect differences.
    if reqif_dialect not in REQIF_SUPPORTED_DIALECTS:
        stats.errors.append(
            "Unknown --reqif-dialect: " + repr(reqif_dialect) + ". "
            "Known: " + repr(list(REQIF_SUPPORTED_DIALECTS)) + ". "
            "Falling back to 'basic'."
        )
        log("WARNING: " + stats.errors[-1])
        reqif_dialect = "basic"

    extra_paths = {}
    for fmt in (emit_extra or ()):
        writer_fn = EXTRA_FORMAT_WRITERS.get(fmt)
        if writer_fn is None:
            stats.errors.append(
                "Unknown --emit format: " + repr(fmt) + ". "
                "Known: " + repr(sorted(EXTRA_FORMAT_WRITERS))
            )
            log("WARNING: " + stats.errors[-1])
            continue
        extra_out = output_path.with_suffix("." + fmt)
        if fmt == "reqif":
            writer_fn(all_reqs, extra_out, dialect=reqif_dialect)
        else:
            writer_fn(all_reqs, extra_out)
        log("Wrote " + fmt.upper() + " to " + str(extra_out) + ".")
        extra_paths[fmt] = extra_out

    return ExtractionResult(
        requirements=all_reqs,
        stats=stats,
        output_path=output_path,
        statement_set_path=stmt_path,
        extra_output_paths=extra_paths,
    )
