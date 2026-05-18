"""korudsl — bidirectional scenario DSL ↔ OQL library transforms.

Canonical home for text DSL parsing, library JSON serialization, and
round-trip validation. No HTTP, IDE, or planfile dependencies.
"""

from __future__ import annotations

from .library import (
    convert_goals_json_to_library,
    ensure_library_structure,
    library_to_dsl,
    normalize_dsl_to_library,
)
from .transform import dsl_roundtrip_report, library_from_any, library_to_any

__all__ = [
    "convert_goals_json_to_library",
    "dsl_roundtrip_report",
    "ensure_library_structure",
    "library_from_any",
    "library_to_any",
    "library_to_dsl",
    "normalize_dsl_to_library",
]
