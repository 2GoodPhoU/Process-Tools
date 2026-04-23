"""Command-line entry point for document-data-extractor.

The CLI is subcommand-based.  Each subcommand drives one extraction
mode.  Adding a new mode is a matter of adding one subparser and wiring
it to its orchestrator function — the shared scaffolding (input
collection, global flags, summary dispatch) stays unchanged.

Usage examples:
    # Requirements mode (default output: requirements.xlsx).
    document-data-extractor requirements spec.docx -o out.xlsx
    document-data-extractor reqs folder/ --actors actors.xlsx --nlp

    # Auto-harvest actors first, then extract requirements in one shot.
    document-data-extractor requirements folder/ --auto-actors -o out.xlsx

    # Tweak HARD/SOFT keyword lists without authoring a full --config.
    document-data-extractor --keywords house_style.yaml requirements folder/

    # Actors mode (default output: actors_scan.xlsx).
    document-data-extractor actors folder/ -o actors.xlsx
    document-data-extractor scan folder/ --actors seed.xlsx --nlp

    # Global flags come before the subcommand:
    document-data-extractor --config my.yaml -q requirements spec.docx

Exit codes:
    0 — success (including a clean --dry-run).
    1 — runtime error the user can fix (corrupt .docx, bad config, I/O).
    2 — usage error (missing inputs, unknown flags).
  130 — interrupted by the user (SIGINT / Ctrl-C).

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


# Exit codes — stable contract for scripted callers.  Keep this block small
# and tightly-scoped; new codes cost forever.
#
#   0 — success (including dry-run success).
#   1 — runtime error the user can fix (corrupt docx, bad config, I/O error).
#   2 — usage error (missing inputs, unknown mode, argparse complaints).
EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2


_REQUIREMENTS_EPILOG = """\
Examples:
  # Basic: one document, default output (requirements.xlsx in CWD).
  document-data-extractor requirements spec.docx

  # A folder of docs + a curated actors list.
  document-data-extractor requirements specs/ --actors actors.xlsx -o out.xlsx

  # Dry run with samples — good for iterating on a new config.
  document-data-extractor requirements specs/ --dry-run --show-samples 5

  # Auto-harvest actors on the fly, then extract requirements.
  document-data-extractor requirements specs/ --auto-actors -o out.xlsx

  # Swap HARD/SOFT keyword lists without writing a full --config.
  document-data-extractor --keywords house_style.yaml requirements specs/
"""

_ACTORS_EPILOG = """\
Examples:
  # Basic: harvest every actor-like string to actors_scan.xlsx.
  document-data-extractor actors specs/

  # Seed with a curated list — seeded rows are preserved verbatim.
  document-data-extractor actors specs/ --actors seed.xlsx -o actors.xlsx

  # Also use spaCy NER (noisier — review the Observations sheet).
  document-data-extractor actors specs/ --nlp
"""


# ---------------------------------------------------------------------------
# Subcommand catalogue.
# ---------------------------------------------------------------------------
#
# Single source of truth for the names the parser accepts, kept next to
# the argparse wiring.  The ``extract.py`` backward-compat shim imports
# this set so it doesn't drift when we add or rename a subcommand.
SUBCOMMAND_NAMES = frozenset({
    # canonical names
    "requirements",
    "actors",
    # aliases — keep in sync with ``aliases=[...]`` on each add_parser call
    "reqs",
    "scan",
})


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


def _is_tty() -> bool:
    """True if stdout looks like an interactive terminal.

    Used to decide whether to carriage-return-update a single progress
    line vs. print each progress message on its own newline.  In
    non-interactive contexts (pipes, log files, CI) the carriage-return
    approach turns into a pile of unreadable control characters, so we
    fall back to plain lines.
    """
    try:
        return bool(sys.stdout.isatty())
    except Exception:  # noqa: BLE001 — some wrappers raise on isatty()
        return False


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
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0  success (also returned for a clean --dry-run).\n"
            "  1  runtime error the user can fix (e.g. corrupt .docx, "
            "bad config).\n"
            "  2  usage error (missing inputs, unknown flags).\n"
            "\n"
            "Run 'document-data-extractor <mode> --help' for per-mode "
            "flags and more examples."
        ),
    )

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
        "--keywords",
        type=Path,
        default=None,
        help=(
            "Optional keywords file (YAML or .txt) that tweaks just the "
            "HARD/SOFT requirement keyword lists — without having to "
            "author a full --config.  Supports 'hard: [...]' to REPLACE "
            "the bucket or 'hard_add:' / 'hard_remove:' to tweak the "
            "defaults.  See samples/sample_keywords.yaml for the schema. "
            "Applied on top of --config; a per-doc '<stem>.reqx.yaml' "
            "still wins over both."
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
        epilog=_REQUIREMENTS_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        "--auto-actors",
        dest="auto_actors",
        action="store_true",
        help=(
            "Run the actor scan on the input docs first and use its output "
            "as the actors list for the requirements pass.  Saves the "
            "'maintain a separate actors.xlsx' step for users who just want "
            "to get going.  Any --actors file you pass is used to seed the "
            "scan and is preserved through to the requirements run.  The "
            "harvested list is written as a sidecar next to --output for "
            "inspection / reuse."
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
        epilog=_ACTORS_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        return EXIT_USAGE

    def progress(msg: str) -> None:
        if not args.quiet:
            # In TTY mode we still print each message on its own line —
            # tqdm-style carriage-return overwriting would require
            # swallowing all output which is more intrusive than this
            # problem deserves.  The tty check is kept so future callers
            # (e.g. a compact mode flag) have the hook.
            print(msg)

    def summary(msg: str) -> None:
        if not args.no_summary:
            print(msg)

    inputs = _collect_docx(args.inputs)
    if not inputs:
        print("No .docx files found.", file=sys.stderr)
        return EXIT_USAGE

    mode = args.mode
    try:
        if mode in ("requirements", "reqs"):
            return _run_requirements(args, inputs, progress, summary)
        if mode in ("actors", "scan"):
            return _run_actors(args, inputs, progress, summary)
    except KeyboardInterrupt:
        # Match the CLI-as-script convention: 130 = terminated by SIGINT.
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except (FileNotFoundError, ValueError, OSError) as exc:
        # These are the user-fixable runtime errors we bubble up — a
        # missing file, a corrupt config, permission denied on the
        # output path.  An unrestricted 'except' would hide real bugs.
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME

    # Shouldn't reach here — argparse already restricted choices.
    print(f"Unknown mode: {mode}", file=sys.stderr)
    return EXIT_USAGE


def _harvest_auto_actors(
    args,
    inputs: List[Path],
    output_path: Path,
    progress,
) -> Path:
    """Run the actor scan as a pre-pass and return the harvested xlsx path.

    Called only when ``--auto-actors`` is set.  Seeds with any explicit
    ``--actors`` file so the user's curated list survives verbatim into
    the sidecar that the requirements pass will consume.
    """
    auto_path = output_path.with_name(f"{output_path.stem}_auto_actors.xlsx")
    progress(f"Auto-actors: harvesting to {auto_path.name} ...")
    scan_result = scan_actors_from_files(
        input_paths=inputs,
        output_path=auto_path,
        seed_actors_xlsx=args.actors,
        use_nlp=args.nlp,
        config_path=args.config,
        keywords_path=args.keywords,
        progress=progress,
    )
    return scan_result.output_path


def _run_requirements(
    args, inputs: List[Path], progress, summary,
) -> int:
    """Requirements-mode dispatch."""
    dry_run = bool(getattr(args, "dry_run", False))
    auto_actors = bool(getattr(args, "auto_actors", False))
    show_samples = int(getattr(args, "show_samples", 0) or 0)

    # When dry-running we don't touch disk, but extract_from_files still
    # wants an output_path — pass the default so error messages make sense
    # if dry_run=False is reintroduced via code-path reuse elsewhere.
    output_path = args.output or Path("requirements.xlsx")

    effective_actors: Optional[Path] = args.actors
    if auto_actors:
        effective_actors = _harvest_auto_actors(args, inputs, output_path, progress)

    result = extract_from_files(
        input_paths=inputs,
        output_path=output_path,
        actors_xlsx=effective_actors,
        use_nlp=args.nlp,
        statement_set_path=None if dry_run else args.statement_set,
        config_path=args.config,
        keywords_path=args.keywords,
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
    return EXIT_OK


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
        keywords_path=args.keywords,
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
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
