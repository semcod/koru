"""Compatibility aliases for the canonical DSL schema registry."""

from dsl2koru.schema_registry import (
    COMMAND_VERBS,
    KORU_DELEGATE_VERBS,
    QUERY_VERBS,
    UI_VERBS,
    _load_schemas,
    all_verbs,
    normalize_verb,
    schema_for_verb,
    validate_schemas,
)

__all__ = [
    "COMMAND_VERBS",
    "KORU_DELEGATE_VERBS",
    "QUERY_VERBS",
    "UI_VERBS",
    "_load_schemas",
    "all_verbs",
    "normalize_verb",
    "schema_for_verb",
    "validate_schemas",
]
