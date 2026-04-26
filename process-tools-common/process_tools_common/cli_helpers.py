"""Small CLI helpers shared by compliance-matrix and nimbus-skeleton.

Both consumer tools historically grew their own ``-q/--quiet`` flag
and a ``log = (lambda *a, **kw: None) if quiet else print`` pattern at
the top of ``main()``. They were identical line-for-line. This module
centralises that boilerplate so the user-visible flag behaviour stays
in one place.

Public surface
--------------

``add_quiet_flag(parser)`` — register the standard ``-q/--quiet``
flag on an ``argparse.ArgumentParser``. Returns the parser for
chaining.

``make_logger(quiet)`` — return a ``print``-shaped callable. When
``quiet=True``, the callable is a no-op; when ``quiet=False``, it
forwards to ``print``. Errors should bypass this and use ``print``
to ``sys.stderr`` directly so they're not silenced.

Why no Python ``logging``? Both tools' progress output is
print-style status (``"Loading requirements..."``, ``"  23 hits"``)
that doesn't benefit from level filters / handlers / formatters. A
real logging migration is a separate item; this helper keeps the
existing semantics 1:1.
"""

from __future__ import annotations

import argparse
from typing import Callable


# Help text is centralised so both tool CLIs print identical wording.
QUIET_HELP = "Suppress progress output (errors still print)."


def add_quiet_flag(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Register the standard ``-q/--quiet`` flag on a parser.

    The flag's ``dest`` is ``quiet`` and it is a boolean store-true.
    Returns ``parser`` for chaining.
    """
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help=QUIET_HELP,
    )
    return parser


def make_logger(quiet: bool) -> Callable[..., None]:
    """Return a ``print``-shaped callable that respects ``quiet``.

    When ``quiet=True`` the callable is a no-op and returns ``None``.
    When ``quiet=False`` it forwards every call to ``print``.
    """
    if quiet:
        def _noop(*_args, **_kwargs) -> None:
            return None

        return _noop
    return print
