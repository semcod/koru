"""High-level DSL transforms and round-trip validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from .library import (
    convert_goals_json_to_library,
    ensure_library_structure,
    library_to_dsl,
    normalize_dsl_to_library,
)

InputKind = Literal["dsl", "goals_json", "library_json", "library"]


def library_from_any(
    payload: str | dict[str, Any] | list[Any],
    *,
    kind: InputKind | None = None,
) -> dict[str, Any]:
    """Normalize arbitrary input into a library dict."""
    if isinstance(payload, dict) and kind in (None, "library"):
        return ensure_library_structure(payload)
    if isinstance(payload, str):
        stripped = payload.strip()
        if kind == "dsl" or (kind is None and "GOAL:" in stripped):
            return normalize_dsl_to_library(stripped)
        if kind in ("goals_json", "library_json", None):
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError:
                return normalize_dsl_to_library(stripped)
            if isinstance(data, dict) and {"goals", "objects", "functions"} & set(data):
                return ensure_library_structure(data)
            return convert_goals_json_to_library(data)
    if isinstance(payload, list):
        return convert_goals_json_to_library(payload)
    raise TypeError(f"unsupported payload type: {type(payload)!r}")


def library_to_any(library: dict[str, Any], *, fmt: Literal["dsl", "json"] = "dsl") -> str:
    if fmt == "json":
        return json.dumps(ensure_library_structure(library), indent=2, sort_keys=True) + "\n"
    return library_to_dsl(library)


def dsl_roundtrip_report(dsl_text: str) -> dict[str, Any]:
    """Parse DSL → library → DSL and report structural equality."""
    first = normalize_dsl_to_library(dsl_text)
    second_text = library_to_dsl(first)
    second = normalize_dsl_to_library(second_text)
    return {
        "ok": first == second,
        "goals_in": len(first.get("goals", [])),
        "goals_out": len(second.get("goals", [])),
        "regenerated_dsl": second_text,
        "library": first,
    }


def load_path(path: Path) -> tuple[InputKind, str | dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".json", ".oql"}:
        return "library_json", text
    if path.suffix.lower() in {".dsl", ".txt", ""}:
        return "dsl", text
    return "dsl", text
