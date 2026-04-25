"""Convenience launcher: ``python run_cli.py --contract ... --procedure ... -o ...``."""

import sys

from compliance_matrix.cli import main


if __name__ == "__main__":
    sys.exit(main())
