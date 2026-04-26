"""argparse CLI entry point.

Usage::

    nimbus-skeleton \
        --requirements path/to/dde_requirements.xlsx \
        --actors       path/to/dde_actors.xlsx \
        --output-dir   path/to/output/

Produces five files in ``--output-dir`` by default:

- ``<basename>.puml``       — PlantUML activity diagram (instant viz)
- ``<basename>.skel.yaml``  — tool-neutral YAML manifest (the pivot file)
- ``<basename>.xmi``        — UML 2.5 XMI (importable into Cameo / EA / MagicDraw)
- ``<basename>.vsdx``       — Visio file (the Nimbus import path)
- ``<basename>.review.xlsx`` — side-car listing every flagged activity

Pass ``--bpmn`` to additionally emit ``<basename>.bpmn`` (BPMN 2.0 XML —
the recommended interchange now that Nimbus on-prem is retired). The
research note at ``research/2026-04-25-stack-alternatives-survey.md``
captures the rationale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .builder import build_skeleton
from .emitters import bpmn, manifest, plantuml, vsdx, xmi
from .loader import load_actors_xlsx, load_dde_xlsx  # also bootstraps process_tools_common on sys.path
from .review_writer import write_review

# Shared helpers — loader.py already added process-tools-common to sys.path.
from process_tools_common.cli_helpers import add_quiet_flag, make_logger


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nimbus-skeleton",
        description=(
            "Turn DDE-extracted requirements into a starter UML activity "
            "diagram. Outputs PlantUML + YAML manifest + UML 2.5 XMI + "
            "Visio (.vsdx) + a review side-car xlsx of items the builder "
            "flagged for human judgment. Pass --bpmn to additionally "
            "emit BPMN 2.0 XML."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"nimbus-skeleton {__version__}",
    )
    parser.add_argument(
        "--requirements",
        required=True,
        type=Path,
        help="DDE requirements xlsx (one row per requirement).",
    )
    parser.add_argument(
        "--actors",
        type=Path,
        default=None,
        help="Optional DDE actors xlsx -- improves alias resolution into swimlanes.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Output directory. Will be created if it doesn't exist.",
    )
    parser.add_argument(
        "--basename",
        default="skeleton",
        help="Base filename for outputs (default: 'skeleton').",
    )
    parser.add_argument(
        "--title",
        default="Process Skeleton",
        help="Diagram title (default: 'Process Skeleton').",
    )
    parser.add_argument(
        "--no-xmi",
        action="store_true",
        help="Skip the XMI emitter.",
    )
    parser.add_argument(
        "--no-vsdx",
        action="store_true",
        help="Skip the Visio (.vsdx) emitter.",
    )
    parser.add_argument(
        "--bpmn",
        action="store_true",
        help=(
            "Also emit a BPMN 2.0 .bpmn file (open-standard process "
            "interchange -- Camunda Modeler, bpmn.io, Signavio, etc.). "
            "Recommended migration path now that TIBCO Nimbus on-prem "
            "is retired (Sept 2025) -- see "
            "research/2026-04-25-stack-alternatives-survey.md."
        ),
    )
    add_quiet_flag(parser)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    log = make_logger(args.quiet)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    log(f"Loading requirements from {args.requirements.name}...")
    rows = load_dde_xlsx(args.requirements)
    log(f"  {len(rows)} requirements")

    actors_overrides = {}
    if args.actors is not None:
        log(f"Loading actors table from {args.actors.name}...")
        actors_overrides = load_actors_xlsx(args.actors)
        log(f"  {len(actors_overrides)} canonical actors")

    log("Building skeleton...")
    skeleton = build_skeleton(rows, actors_overrides=actors_overrides)
    log(
        f"  actors={len(skeleton.actors)}  activities={len(skeleton.activities)}  "
        f"gateways={len(skeleton.gateways)}  notes={len(skeleton.notes)}  "
        f"flows={len(skeleton.flows)}  flagged={len(skeleton.review_records())}"
    )

    puml_path = args.output_dir / f"{args.basename}.puml"
    yaml_path = args.output_dir / f"{args.basename}.skel.yaml"
    xmi_path = args.output_dir / f"{args.basename}.xmi"
    vsdx_path = args.output_dir / f"{args.basename}.vsdx"
    bpmn_path = args.output_dir / f"{args.basename}.bpmn"
    review_path = args.output_dir / f"{args.basename}.review.xlsx"

    log(f"Writing PlantUML to {puml_path}...")
    plantuml.write(skeleton, puml_path, title=args.title)

    log(f"Writing manifest to {yaml_path}...")
    manifest.write(skeleton, yaml_path, title=args.title)

    if not args.no_xmi:
        log(f"Writing XMI to {xmi_path}...")
        xmi.write(skeleton, xmi_path, title=args.title)

    if not args.no_vsdx:
        log(f"Writing Visio (.vsdx) to {vsdx_path}...")
        vsdx.write(skeleton, vsdx_path, title=args.title)

    if args.bpmn:
        log(f"Writing BPMN 2.0 to {bpmn_path}...")
        bpmn.write(skeleton, bpmn_path, title=args.title)

    log(f"Writing review side-car to {review_path}...")
    write_review(skeleton, review_path, dde_rows=rows)

    log(
        f"Done. Render the .puml at https://www.plantuml.com/plantuml/uml/, "
        f"open the .vsdx in Visio (or import directly to Nimbus via "
        f"File -> Import/Export -> Import from Visio), or open the "
        f".review.xlsx to triage flagged items."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
