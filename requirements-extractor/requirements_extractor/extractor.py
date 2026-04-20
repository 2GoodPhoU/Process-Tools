"""High-level orchestrator — put all pieces together."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from .actors import ActorResolver, load_actors_from_xlsx
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


def extract_from_files(
    input_paths: Sequence[Path],
    output_path: Path,
    *,
    actors_xlsx: Optional[Path] = None,
    use_nlp: bool = False,
    statement_set_path: Optional[Path] = None,
    progress: Optional[Callable[[str], None]] = None,
) -> ExtractionResult:
    """Parse every .docx in `input_paths` and write results.

    Always writes the Excel workbook at `output_path`.  If
    `statement_set_path` is provided, additionally writes a statement-set
    CSV in the hierarchical (Level N, Description N) format.
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

    all_reqs: List[Requirement] = []
    events_per_file: List[Tuple[str, List[object]]] = []

    for path in input_paths:
        path = Path(path)
        if not path.exists():
            stats.errors.append(f"File not found: {path}")
            log(f"WARNING: {stats.errors[-1]}")
            continue
        if path.suffix.lower() != ".docx":
            stats.errors.append(f"Skipping non-.docx file: {path.name}")
            log(f"WARNING: {stats.errors[-1]}")
            continue

        log(f"Parsing {path.name} ...")
        try:
            events = parse_docx_events(path, resolver_fn=resolver.resolve)
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
