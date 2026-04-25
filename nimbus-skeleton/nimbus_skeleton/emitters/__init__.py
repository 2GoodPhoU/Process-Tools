"""Output-format emitters.

Each module exposes ``render(skeleton, **opts) -> str`` for text formats
or ``write(skeleton, output_path, **opts) -> None`` for multi-file /
binary formats.
"""

from . import bpmn, manifest, plantuml, vsdx, xmi

__all__ = ["plantuml", "manifest", "xmi", "vsdx", "bpmn"]
