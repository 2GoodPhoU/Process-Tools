"""Convenience entry point so you can run `python extract.py ...`
instead of `python -m requirements_extractor.cli ...`.

Backward-compat shim: the CLI is now subcommand-based (``requirements``,
``actors``).  If someone invokes this the old flag-style way
(``python extract.py spec.docx -o out.xlsx``) with no subcommand,
we transparently prepend ``requirements`` so existing scripts keep
working.  Any argv that already names a subcommand (or asks for help)
is passed through untouched.
"""

from __future__ import annotations

import sys

from requirements_extractor.cli import main

# Subcommand names (and aliases) that main() understands.  Kept in sync
# with requirements_extractor.cli.build_parser.
_KNOWN_SUBCOMMANDS = {"requirements", "reqs", "actors", "scan"}
# Top-level flags that may appear before a subcommand.  If we see one
# of these, we scan past it to check whether a subcommand follows.
_GLOBAL_FLAGS_WITH_VALUE = {"--config"}
_GLOBAL_FLAGS_NO_VALUE = {"-q", "--quiet", "--no-summary"}
_HELP_FLAGS = {"-h", "--help"}


def _needs_default_subcommand(argv: list[str]) -> bool:
    """Return True if argv has no subcommand and we should inject one."""
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in _HELP_FLAGS:
            return False  # let argparse show help
        if tok in _KNOWN_SUBCOMMANDS:
            return False
        if tok in _GLOBAL_FLAGS_WITH_VALUE:
            i += 2  # consume flag + its value
            continue
        if tok in _GLOBAL_FLAGS_NO_VALUE:
            i += 1
            continue
        # Any other token (positional, unknown flag) means the user
        # isn't using a subcommand — default to 'requirements'.
        return True
    # Pure empty / all-global-flags case: no subcommand → show help,
    # which is what main() already does.  Don't inject.
    return False


def _compat_argv(argv: list[str]) -> list[str]:
    """Inject ``requirements`` before the first non-flag positional if needed."""
    if not _needs_default_subcommand(argv):
        return argv
    out = list(argv)
    i = 0
    while i < len(out):
        tok = out[i]
        if tok in _GLOBAL_FLAGS_WITH_VALUE:
            i += 2
            continue
        if tok in _GLOBAL_FLAGS_NO_VALUE:
            i += 1
            continue
        # First non-global token — insert 'requirements' here.
        out.insert(i, "requirements")
        return out
    # Shouldn't reach: _needs_default_subcommand returned True so there
    # must be a non-global token somewhere.
    return out


if __name__ == "__main__":
    raise SystemExit(main(_compat_argv(sys.argv[1:])))
