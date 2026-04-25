"""Matcher implementations.

Each matcher exposes a single ``run(contract_rows, procedure_rows, **opts) ->
list[Match]`` function. The combiner imports them as a list and runs each in
turn; matchers don't know about each other.
"""

from . import explicit_id, fuzzy_id, keyword_overlap, manual_mapping, similarity

__all__ = ["explicit_id", "fuzzy_id", "keyword_overlap", "manual_mapping", "similarity"]
