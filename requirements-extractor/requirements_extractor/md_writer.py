"""Compatibility shim — the Markdown writer lives in :mod:`writers_extra`.

This module exists only so callers that imported ``md_writer`` in an
earlier pass don't break.  New code should ``from .writers_extra
import write_requirements_md`` directly.
"""

from .writers_extra import write_requirements_md  # noqa: F401
