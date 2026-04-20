"""Convenience entry point so you can run `python extract.py ...`
instead of `python -m requirements_extractor.cli ...`.
"""

from requirements_extractor.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
