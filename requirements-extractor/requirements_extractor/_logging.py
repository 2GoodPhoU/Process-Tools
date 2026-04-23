"""Shared logging plumbing for the extractor pipelines.

The CLI and GUI already route user-visible progress messages through a
``progress: Callable[[str], None]`` callback.  This module adds a parallel
route through :mod:`logging` — specifically the ``requirements_extractor``
logger — so scripted callers and tests can dial verbosity, capture
output, or route to syslog without having to supply a callback.

A ``NullHandler`` is attached on import (standard-library recommendation
for libraries) so importing this package never adds noise to a host
application's root logger unless that application opts in.

Level routing is a simple heuristic based on the message prefix the
existing code already uses:

    "ERROR: …"   → ``logger.error``
    "WARNING: …" → ``logger.warning``
    otherwise    → ``logger.info``

Callers who want structured logging should use :data:`logger` directly.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger("requirements_extractor")
logger.addHandler(logging.NullHandler())


ProgressCallback = Callable[[str], None]


def make_progress_logger(
    progress: Optional[ProgressCallback],
) -> ProgressCallback:
    """Return a callback that forwards to ``progress`` and to the logger.

    If ``progress`` is None, only the logger is used (so a quiet CLI
    still emits debuggable records when someone attaches a handler).
    """
    fallback: ProgressCallback = progress or (lambda _msg: None)

    def _emit(msg: str) -> None:
        if msg.startswith("ERROR"):
            logger.error("%s", msg)
        elif msg.startswith("WARNING"):
            logger.warning("%s", msg)
        else:
            logger.info("%s", msg)
        fallback(msg)

    return _emit
