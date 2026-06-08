"""JSON Schema registry for dsl2koru commands."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

QUERY_VERBS = frozenset({"QUERY_REPAIR_HISTORY", "QUERY_LANE_STATUS", "VALIDATE_LANE", "RESOLVE"})
COMMAND_VERBS = frozenset({"REPAIR_RUN"})


@lru_cache(maxsize=1)
def _load_schemas() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    pkg = resources.files("dsl2koru").joinpath("schema/commands")
    for path in pkg.iterdir():
        if path.name.endswith(".schema.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            verb = str(data.get("properties", {}).get("verb", {}).get("const", ""))
            if verb:
                schemas[verb] = data
    return schemas


def schema_for_verb(verb: str) -> dict[str, Any]:
    schema = _load_schemas().get(verb.upper())
    if schema is None:
        raise KeyError(f"unknown verb schema: {verb}")
    return schema


def all_verbs() -> list[str]:
    return sorted(_load_schemas().keys())


def validate_schemas() -> list[str]:
    errors: list[str] = []
    for verb, data in _load_schemas().items():
        const = data.get("properties", {}).get("verb", {}).get("const")
        if const != verb:
            errors.append(f"{verb}: verb const mismatch {const!r}")
    return errors
