"""Canonical JSON Schema registry for both DSL command-name families."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

QUERY_VERBS = frozenset(
    {
        "STATUS",
        "REPAIR_HISTORY",
        "ENV",
        "QUERY",
        "QUERY_REPAIR_HISTORY",
        "QUERY_LANE_STATUS",
        "VALIDATE_LANE",
        "RESOLVE",
    }
)
COMMAND_VERBS = frozenset(
    {
        "AUTO",
        "LANE",
        "ENSURE",
        "DOCTOR",
        "CALIBRATION",
        "CHAT",
        "TEXT",
        "SYNC",
        "REPAIR_RUN",
        "UI_CAPTURE",
        "UI_TYPE",
        "UI_KEY",
        "UI_CLICK",
        "UI_NL",
    }
)
UI_VERBS = frozenset({"UI_CAPTURE", "UI_TYPE", "UI_KEY", "UI_CLICK", "UI_NL"})
KORU_DELEGATE_VERBS = frozenset({"QUERY_REPAIR_HISTORY", "QUERY_LANE_STATUS", "VALIDATE_LANE", "RESOLVE", "REPAIR_RUN"})

_VERB_ALIASES = {
    "DIAGNOSE": "STATUS",
    "AUTONOMOUS": "AUTO",
    "ASK": "CHAT",
    "LANE_STATUS": "LANE",
    "REPAIR": "REPAIR_RUN",
    "ENVFILE": "ENV",
}


def normalize_verb(raw: str) -> str:
    verb = " ".join(raw.strip().upper().split("-")).replace(" ", "_")
    return _VERB_ALIASES.get(verb, verb)


def _merge_schema(base: dict[str, Any], extension: dict[str, Any]) -> dict[str, Any]:
    merged = {**base, **extension}
    merged["properties"] = {**base.get("properties", {}), **extension.get("properties", {})}
    base_required = set(base.get("required", []))
    extension_required = set(extension.get("required", []))
    merged["required"] = sorted(base_required & extension_required)
    return merged


@lru_cache(maxsize=1)
def _load_schemas() -> dict[str, dict[str, Any]]:
    package = resources.files("dsl2koru")
    compat = json.loads(package.joinpath("schema/compat_commands.json").read_text(encoding="utf-8"))
    schemas: dict[str, dict[str, Any]] = dict(compat)
    for path in package.joinpath("schema/commands").iterdir():
        if not path.name.endswith(".schema.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        verb = str(data.get("properties", {}).get("verb", {}).get("const", ""))
        if not verb:
            continue
        schemas[verb] = _merge_schema(schemas[verb], data) if verb in schemas else data
    return schemas


def schema_for_verb(verb: str) -> dict[str, Any]:
    schema = _load_schemas().get(normalize_verb(verb))
    if schema is None:
        raise KeyError(f"unknown verb schema: {verb}")
    return schema


def all_verbs() -> list[str]:
    return sorted(_load_schemas())


def validate_schemas() -> list[str]:
    errors: list[str] = []
    for verb, data in _load_schemas().items():
        const = data.get("properties", {}).get("verb", {}).get("const")
        if const != verb:
            errors.append(f"{verb}: verb const mismatch {const!r}")
    return errors
