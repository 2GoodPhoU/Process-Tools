"""Compatibility shim — the JSON writer lives in :mod:`writers_extra`.

This module exists only so callers that imported ``json_writer`` in an
earlier pass don't break.  New code should ``from .writers_extra
import write_requirements_json, requirement_to_dict`` directly.
"""

from .writers_extra import requirement_to_dict, write_requirements_json  # noqa: F401
