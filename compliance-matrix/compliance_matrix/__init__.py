"""Compliance Matrix Generator — cross-reference contract requirements against
procedure / standard clauses to produce a traceability matrix.

Inputs are two xlsx workbooks produced by Document Data Extractor (DDE):
one for the contract / spec side, one for the procedure / standard side.
Output is an xlsx coverage matrix (rows = contract requirements,
columns = procedure clauses, cell values encode match strength and which
matcher fired).

Four matcher strategies run in parallel and their results are combined:

- ``explicit_id``    — regex-detected references in the requirement text
  (``IAW [DO-178C §6.3.1]``, ``per Section 4.2.2``, etc.).
- ``keyword_overlap`` — token-Jaccard similarity, no external deps.
- ``similarity``     — TF-IDF cosine similarity, pure-stdlib implementation.
- ``manual_mapping`` — operator-curated yaml/csv mapping file.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
