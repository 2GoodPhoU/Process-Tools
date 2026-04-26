"""DEPRECATED -- removed 2026-04-25.

The compatibility shim that re-exported from ``writers_extra`` has
been removed. New code should import directly:

    from requirements_extractor.writers_extra import (
        requirement_to_dict,
        write_requirements_json,
    )

This module raises on import to fail loudly rather than silently
return stale exports. The file itself can be deleted; it stays here
as a placeholder so a `git status` shows the removal explicitly.
"""

raise ImportError(
    "requirements_extractor.json_writer was removed 2026-04-25. "
    "Import from requirements_extractor.writers_extra instead "
    "(write_requirements_json, requirement_to_dict)."
)
