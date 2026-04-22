"""Command-line entry point for document-data-extractor.

The CLI is subcommand-based.  Each subcommand drives one extraction
mode.  Adding a new mode is a matter of adding one subparser and wiring
it to its orchestrator function — the shared scaffolding (input
collection, global flags, summary dispatch) stays unchanged.

Usage examples:
    # Requirements mode (default output: requirements.xlsx).
    document-data-extractor requirements spec.docx -o out.xlsx
    document-data-extractor reqs folder/ --actors actors.xlsx --nlp

    # Actors mode (default output: actors_scan.xlsx).
    document-data-extractor actors folder/ -o actors.xlsx
    document-data-extractor scan folder/ --actors seed.xlsx --nlp

    # Global flags come before the subcommand:
    document-data-extractor --config my.yaml -q requirements spec.docx

The legacy ``extract.py`` shim keeps working by defaulting to the
``requirements`` subcommand when no subcommand is given, so older
scripts that used the flag-style CLI don't break immediately.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .actor_scan import scan_actors_from_files
from .extractor import extract_from_files


PROG_NAME = "document-data-extractor"
DESCRIPTION = (
    "Pull structured data out of Word (.docx) specifications.  "
    "Requirements mode extracts rows into an Excel workbook; actors mode "
    "harvests a canonical actors list you can feed back in on the next run."
)


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _collect_docx(paths: Sequence[Path]) -> List[Path]:
    """Expand directories into their .docx children; drop everything else."""
    out: List[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(p.rglob("*.docx")))
        else:
            out.append(p)
    # Filter out Word's temporary lock files (~$foo.docx).
    return [p for p in out if not p.name.startswith("~$")]


# ---------------------------------------------------------------------------
# Parser.
# ---------------------------------------------------------------------------


def _add_common_inputs(sp: argparse.ArgumentParser) -> None:
    """Shared positional + output arguments for every subcommand."""
    sp.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="One or more .docx files, or folders containing .docx files.",
    )
    sp.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help=(
            "Path for the output file.  Default depends on the mode "
            "(requirements.xlsx / actors_scan.xlsx)."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROG_NAME, description=DESCRIPTION)

    # --- global flags (before subcommand) --- #
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Path to a YAML config that hints at the document format "
            "(section prefixes, tables to skip, keyword tuning, content "
            "filters). See samples/sample_config.yaml for the full schema. "
            "A per-doc '<stem>.reqx.yaml' next to any .docx is auto-loaded "
            "and overrides the per-run config for that file."
        ),
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress per-file progress output.  The final summary still prints.",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Also suppress the final summary block (useful for scripted runs).",
    )

    # --- subparsers --- #
    sub = parser.add_subparsers(
        dest="mode",
        metavar="MODE",
        title="extraction modes",
    )

    # requirements ------------------------------------------------------- #
    p_req = sub.add_parser(
        "requirements",
        aliases=["reqs"],
        help="Extract requirements rows into an Excel workbook.",
        description=(
            "Walk the input .docx files, detect requirement sentences (Hard / "
            "Soft / Polarity), and write a formatted Excel workbook with one "
            "row per requirement."
        ),
    )
    _add_common_inputs(p_req)
    p_req.add_argument(
        "--actors",
        type=Path,
        default=None,
        help=(
            "Optional Excel file listing known actors (columns: 'Actor', "
            "'Aliases').  Used to find secondary actors in requirement text."
        ),
    )
    p_req.add_argument(
        "--nlp",
        action="store_true",
        help=(
            "Also run spaCy NER to find secondary actors (requires "
            "'pip install spacy' plus an English model)."
        ),
    )
    p_req.add_argument(
        "--statement-set",
        dest="statement_set",
        type=Path,
        default=None,
        help=(
            "Also export a statement-set CSV using the paired "
            "(Level N, Description N) hierarchical format."
        ),
    )
    p_req.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help=(
            "Parse and detect as usual, but do NOT write any Excel or CSV "
            "output.  Useful for previewing counts, iterating on config, "
            "or verifying a new corpus without overwriting prior results."
        ),
    )
    p_req.add_argument(
        "--show-samples",
        dest="show_samples",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Print the first N detected requirements as part of the "
            "summary.  Pairs well with --dry-run for quick sanity checks."
        ),
    )

    # actors ------------------------------------------------------------- #
    p_actors = sub.add_parser(
        "actors",
        aliases=["scan"],
        help="Harvest a canonical actors list from the input docs.",
        description=(
            "Walk the input .docx files WITHOUT requirement detection and "
            "collect every actor-like string (primary-column text + "
            "regex/NER hits).  Emit a workbook whose first sheet has the "
            "'Actor'/'Aliases' columns consumable by 'requirements --actors'."
        ),
    )
    _add_common_inputs(p_actors)
    p_actors.add_argument(
        "--actors",
        type=Path,
        default=None,
        dest="actors",
        help=(
            "Optional seed actors file.  Canonicals and curated aliases are "
            "preserved verbatim in the output; newly observed spellings are "
            "added as extra aliases."
        ),
    )
    p_actors.add_argument(
        "--nlp",
        action="store_true",
        help=(
            "Also run spaCy NER to discover secondary actors.  Yields noisier "
            "candidates — review the Observations sheet before re-feeding."
        ),
    )

    return parser


# ---------------------------------------------------------------------------
# Dispatch.
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Require a subcommand — print help if missing instead of crashing.
    if not getattr(args, "mode", None):
        parser.print_help(sys.stderr)
        return 2

    def progress(msg: str) -> None:
        if not args.quiet:
            print(msg)

    def summary(msg: str) -> None:
        if not args.no_summary:
            print(msg)

    inputs = _collect_docx(args.inputs)
    if not inputs:
        print("No .docx files found.", file=sys.stderr)
        return 2

    mode = args.mode
    if mode in ("requirements", "reqs"):
        return _run_requirements(args, inputs, progress, summary)
    if mode in ("actors", "scan"):
        return _run_actors(args, inputs, progress, summary)

    # Shouldn't reach here — argparse already restricted choices.
    print(f"Unknown mode: {mode}", file=sys.stderr)
    return 2


def _run_requirements(
    args, inputs: List[Path], progress, summary,
) -> int:
    """Requirements-mode dispatch."""
    dry_run = bool(getattr(args, "dry_run", False))
    show_samples = int(getattr(args, "show_samples", 0) or 0)

    # When dry-running we don't touch disk, but extract_from_files still
    # wants an output_path — pass the default so error messages make sense
    # if dry_run=False is reintroduced via code-path reuse elsewhere.
    output_path = args.output or Path("requirements.xlsx")
    result = extract_from_files(
        input_paths=inputs,
        output_path=output_path,
        actors_xlsx=args.actors,
        use_nlp=args.nlp,
        statement_set_path=None if dry_run else args.statement_set,
        config_path=args.config,
        progress=progress,
        dry_run=dry_run,
    )
    summary("")
    summary("==== Summary ====" + ("  [dry run — no files written]" if dry_run else ""))
    summary(f"Files processed:      {result.stats.files_processed}")
    summary(f"Requirements found:   {result.stats.requirements_found}")
    summary(f"  Hard:               {result.stats.hard_count}")
    summary(f"  Soft (needs review):{result.stats.soft_count}")
    if result.stats.errors:
        summary(f"Warnings/Errors:      {len(result.stats.errors)}")
        for err in result.stats.errors:
            summary(f"  - {err}")
    if result.output_path is not None:
        summary(f"Output:               {result.output_path}")
    if result.statement_set_path is not None:
        summary(f"Statement-set CSV:    {result.statement_set_path}")
    if dry_run and args.statement_set is not None:
        summary(f"Statement-set CSV:    (skipped — dry run) {args.statement_set}")

    if show_samples > 0 and result.requirements:
        summary("")
        summary(f"First {min(show_samples, len(result.requirements))} sample(s):")
        for req in result.requirements[:show_samples]:
            # One-line preview; truncate long requirement text so the
            # terminal doesn't wrap aggressively.
            text = req.text if len(req.text) <= 110 else req.text[:107] + "..."
            summary(f"  {req.stable_id}  [{req.req_type}] {req.primary_actor}: {text}")
    return 0


def _run_actors(
    args, inputs: List[Path], progress, summary,
) -> int:
    """Actors-mode dispatch."""
    output_path = args.output or Path("actors_scan.xlsx")
    result = scan_actors_from_files(
        input_paths=inputs,
        output_path=output_path,
        seed_actors_xlsx=args.actors,
        use_nlp=args.nlp,
        config_path=args.config,
        progress=progress,
    )
    summary("")
    summary("==== Actor scan summary ====")
    summary(f"Files processed:   {result.stats.files_processed}")
    summary(f"Observations:      {result.stats.observations}")
    summary(f"Actor groups:      {result.stats.groups}")
    if result.stats.errors:
        summary(f"Warnings/Errors:   {len(result.stats.errors)}")
        for err in result.stats.errors:
            summary(f"  - {err}")
    summary(f"Output:            {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
