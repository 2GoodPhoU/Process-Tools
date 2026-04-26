"""argparse CLI entry point.

Usage::

    compliance-matrix \
        --contract path/to/contract_dde.xlsx \
        --procedure path/to/procedure_dde.xlsx \
        --mapping path/to/manual_mapping.yaml \
        -o coverage_matrix.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .combiner import combine
from .loader import load_pair  # noqa: F401  (also bootstraps process_tools_common on sys.path)
from .matchers import explicit_id, fuzzy_id, keyword_overlap, manual_mapping, similarity
from .matrix_writer import write_matrix

# Shared helpers — loader.py already added process-tools-common to sys.path.
from process_tools_common.cli_helpers import add_quiet_flag, make_logger


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compliance-matrix",
        description=(
            "Cross-reference contract requirements against procedure / "
            "standard clauses. Inputs are two DDE-produced xlsx workbooks; "
            "output is a coverage matrix xlsx."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"compliance-matrix {__version__}",
    )
    parser.add_argument(
        "--contract",
        required=True,
        type=Path,
        help="DDE xlsx for the contract / spec side.",
    )
    parser.add_argument(
        "--procedure",
        required=True,
        type=Path,
        help="DDE xlsx for the procedure / standard side.",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=None,
        help="Optional yaml/csv file with operator-curated id-to-id mappings.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="Path to write the coverage matrix xlsx.",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.20,
        help="TF-IDF cosine cutoff (default: 0.20).",
    )
    parser.add_argument(
        "--keyword-threshold",
        type=float,
        default=0.15,
        help="Keyword Jaccard cutoff (default: 0.15).",
    )
    parser.add_argument(
        "--no-similarity",
        action="store_true",
        help="Skip TF-IDF similarity matcher.",
    )
    parser.add_argument(
        "--no-keyword-overlap",
        action="store_true",
        help="Skip keyword-overlap matcher.",
    )
    parser.add_argument(
        "--no-explicit-id",
        action="store_true",
        help="Skip explicit-id matcher.",
    )
    parser.add_argument(
        "--no-fuzzy-id",
        action="store_true",
        help="Skip fuzzy-id matcher (typo-tolerant section refs).",
    )
    parser.add_argument(
        "--fuzzy-id-threshold",
        type=float,
        default=0.85,
        help="Fuzzy-id matcher similarity threshold (default: 0.85, range 0.0-1.0).",
    )
    add_quiet_flag(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    log = make_logger(args.quiet)

    log(f"Loading {args.contract.name} (contract side)...")
    contract_rows, procedure_rows = load_pair(args.contract, args.procedure)
    log(f"  contract: {len(contract_rows)} rows")
    log(f"  procedure: {len(procedure_rows)} rows")

    all_matches = []

    if not args.no_explicit_id:
        log("Running explicit_id matcher...")
        hits = explicit_id.run(contract_rows, procedure_rows)
        log(f"  {len(hits)} hits")
        all_matches.extend(hits)

    if not args.no_keyword_overlap:
        log(f"Running keyword_overlap (threshold={args.keyword_threshold})...")
        hits = keyword_overlap.run(
            contract_rows, procedure_rows, threshold=args.keyword_threshold
        )
        log(f"  {len(hits)} hits")
        all_matches.extend(hits)

    if not args.no_similarity:
        log(f"Running similarity (threshold={args.similarity_threshold})...")
        hits = similarity.run(
            contract_rows, procedure_rows, threshold=args.similarity_threshold
        )
        log(f"  {len(hits)} hits")
        all_matches.extend(hits)

    if args.mapping is not None:
        log(f"Loading manual mapping from {args.mapping.name}...")
        hits = manual_mapping.run(
            contract_rows, procedure_rows, mapping_path=args.mapping
        )
        log(f"  {len(hits)} hits")
        all_matches.extend(hits)

    if not args.no_fuzzy_id:
        log(f"Running fuzzy_id (threshold={args.fuzzy_id_threshold})...")
        hits = fuzzy_id.run(
            contract_rows, procedure_rows, threshold=args.fuzzy_id_threshold
        )
        log(f"  {len(hits)} hits")
        all_matches.extend(hits)

    log(f"Combining {len(all_matches)} matcher records...")
    combined = combine(all_matches)
    log(f"  {len(combined)} unique (req, clause) pairs")

    log(f"Writing coverage matrix to {args.output}...")
    write_matrix(contract_rows, procedure_rows, combined, args.output)

    # Quick coverage summary
    covered_reqs = {key[0] for key in combined.keys()}
    coverage_pct = (
        100.0 * len(covered_reqs) / len(contract_rows) if contract_rows else 0.0
    )
    log(
        f"Coverage: {len(covered_reqs)}/{len(contract_rows)} requirements "
        f"({coverage_pct:.1f}%) have at least one procedure match."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
