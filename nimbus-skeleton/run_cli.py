"""Convenience launcher: ``python run_cli.py --requirements ... --output-dir ...``."""

import sys

from nimbus_skeleton.cli import main


if __name__ == "__main__":
    sys.exit(main())
