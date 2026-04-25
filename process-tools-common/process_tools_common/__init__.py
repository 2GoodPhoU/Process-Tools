"""Shared utilities for the Process-Tools workshop.

The three downstream tools (Document Data Extractor, Compliance Matrix
Generator, Nimbus Skeleton Mapper) share a few primitives — most
notably the DDE xlsx schema. This package centralises those primitives
so a future DDE column rename only needs one update.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
