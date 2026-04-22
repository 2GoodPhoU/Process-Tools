"""Command-line entry point.

Usage examples:
    python -m requirements_extractor.cli spec.docx -o out.xlsx
    python -m requirements_extractor.cli folder/ -o out.xlsx --actors actors.xlsx
    python -m requirements_extractor.cli spec1.docx spec2.docx -o out.xlsx --nlp
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from .extractor import extract_from_files


def _collect_docx(paths: List[Path]) -> List[Path]:
    """Expand directories into their .docx children; drop everything else."""
    out: List[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(p.rglob("*.docx")))
        else:
            out.append(p)
    # Filter out Word's temporary lock files (~$foo.docx).
    return [p for p in out if not p.name.startswith("~$")]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="requirements-extractor",
        description=(
            "Extract requirements (source | actor | requirement) from .docx "
            "specifications into a formatted Excel workbook."
        ),
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="One or more .docx files, or folders containing .docx files.",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("requirements.xlsx"),
        help="Path for the output .xlsx (default: requirements.xlsx).",
    )
    parser.add_argument(
        "--actors",
        type=Path,
        default=None,
        help=(
            "Optional Excel file listing known actors. "
            "Columns: 'Actor' (required), 'Aliases' (optional, comma-separated)."
        ),
    )
    parser.add_argument(
        "--nlp",
        action="store_true",
        help=(
            "Also run spaCy NER to find secondary actors (requires "
            "'pip install spacy' plus an English model)."
        ),
    )
    parser.add_argument(
        "--statement-set",
        dest="statement_set",
        type=Path,
        default=None,
        help=(
            "Also export a statement-set CSV to the given path, using the "
            "paired (Level N, Description N) hierarchical format."
        ),
    )
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
    return parser


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    inputs = _collect_docx(args.inputs)
    if not inputs:
        print("No .docx files found.", file=sys.stderr)
        return 2

    def progress(msg: str) -> None:
        if not args.quiet:
            print(msg)

    def summary(msg: str) -> None:
        if not args.no_summary:
            print(msg)

    result = extract_from_files(
        input_paths=inputs,
        output_path=args.output,
        actors_xlsx=args.actors,
        use_nlp=args.nlp,
        statement_set_path=args.statement_set,
        config_path=args.config,
        progress=progress,
    )

    summary("")
    summary("==== Summary ====")
    summary(f"Files processed:      {result.stats.files_processed}")
    summary(f"Requirements found:   {result.stats.requirements_found}")
    summary(f"  Hard:               {result.stats.hard_count}")
    summary(f"  Soft (needs review):{result.stats.soft_count}")
    if result.stats.errors:
        summary(f"Warnings/Errors:      {len(result.stats.errors)}")
        for err in result.stats.errors:
            summary(f"  - {err}")
    summary(f"Output:               {result.output_path}")
    if result.statement_set_path is not None:
        summary(f"Statement-set CSV:    {result.statement_set_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
