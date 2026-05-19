"""DSL text ↔ OQL library JSON (bidirectional)."""

from __future__ import annotations

import json
from typing import Any


def ensure_library_structure(library: dict[str, Any] | None) -> dict[str, Any]:
    """Return library dict with required top-level keys."""
    out = dict(library) if library is not None else {}
    out.setdefault("goals", [])
    out.setdefault("objects", {})
    out.setdefault("functions", {})
    return out


def _start_goal(library: dict[str, Any], line: str) -> dict[str, Any] | None:
    goal_name = line[5:].strip()
    if not goal_name:
        return None
    goal: dict[str, Any] = {"name": goal_name, "steps": [], "objectives": []}
    library["goals"].append(goal)
    return goal


def _handle_func(line: str, goal: dict[str, Any] | None, library: dict[str, Any]) -> None:
    func_name = line[5:].strip()
    if func_name and goal is not None:
        library["functions"][func_name] = {"type": "function", "code": line}


def _handle_set(line: str, goal: dict[str, Any] | None) -> None:
    if goal is not None:
        goal["steps"].append({"type": "set", "instruction": line})


def _handle_wait(line: str, goal: dict[str, Any] | None) -> None:
    if goal is not None:
        goal["steps"].append({"type": "wait", "duration": line[5:].strip()})


def _handle_get(line: str, goal: dict[str, Any] | None) -> None:
    if goal is not None:
        goal["steps"].append({"type": "get", "variable": line[4:].strip()})


def _handle_save(line: str, goal: dict[str, Any] | None) -> None:
    if goal is not None:
        goal["steps"].append({"type": "save", "key": line[5:].strip()})


def _handle_if(line: str, goal: dict[str, Any] | None) -> None:
    if goal is not None:
        goal["steps"].append({"type": "if", "condition": line[3:].strip()})


def _handle_error(line: str, goal: dict[str, Any] | None) -> None:
    if goal is not None:
        goal["objectives"].append(
            {"type": "error", "message": line[6:].strip().strip("\"'")},
        )


def _handle_correct(line: str, goal: dict[str, Any] | None) -> None:
    if goal is not None:
        goal["objectives"].append(
            {"type": "success", "message": line[8:].strip().strip("\"'")},
        )


_PREFIX_HANDLERS: tuple[tuple[str, Any], ...] = (
    ("FUNC:", _handle_func),
    ("SET ", _handle_set),
    ("WAIT ", _handle_wait),
    ("GET ", _handle_get),
    ("SAVE ", _handle_save),
    ("IF ", _handle_if),
    ("ERROR ", _handle_error),
    ("CORRECT ", _handle_correct),
)


def _apply_prefixed_line(
    line: str,
    goal: dict[str, Any] | None,
    library: dict[str, Any],
) -> bool:
    for prefix, handler in _PREFIX_HANDLERS:
        if not line.startswith(prefix):
            continue
        if prefix == "FUNC:":
            _handle_func(line, goal, library)
        else:
            handler(line, goal)
        return True
    return False


def normalize_dsl_to_library(
    dsl_text: str,
    existing_library: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert DSL text to OQL library JSON structure."""
    library = ensure_library_structure(existing_library)
    if not dsl_text or not dsl_text.strip():
        return library

    current_goal: dict[str, Any] | None = None
    for raw in dsl_text.strip().split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("GOAL:"):
            current_goal = _start_goal(library, line)
            continue
        _apply_prefixed_line(line, current_goal, library)
    return library


def convert_goals_json_to_library(
    goals_json: str | list[Any] | dict[str, Any],
    existing_library: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert legacy goals JSON to OQL library."""
    library = ensure_library_structure(existing_library)
    if not goals_json or (isinstance(goals_json, str) and not goals_json.strip()):
        return library

    try:
        goals_data = json.loads(goals_json) if isinstance(goals_json, str) else goals_json
        if isinstance(goals_data, dict) and "goals" in goals_data:
            goals_data = goals_data["goals"]
        if isinstance(goals_data, list):
            library["goals"] = goals_data
    except (json.JSONDecodeError, TypeError):
        pass
    return library


def _emit_step(step: dict[str, Any]) -> list[str]:
    stype = str(step.get("type") or "").lower()
    if stype == "set":
        instr = step.get("instruction")
        return [str(instr) if instr else "SET "]
    if stype == "wait":
        return [f"WAIT {step.get('duration', '')}".rstrip()]
    if stype == "get":
        return [f"GET {step.get('variable', '')}".rstrip()]
    if stype == "save":
        return [f"SAVE {step.get('key', '')}".rstrip()]
    if stype == "if":
        return [f"IF {step.get('condition', '')}".rstrip()]
    return [f"# unknown step type: {stype}"]


def _emit_objective(obj: dict[str, Any]) -> str | None:
    otype = str(obj.get("type") or "").lower()
    msg = str(obj.get("message") or "")
    if otype == "error":
        return f'ERROR "{msg}"'
    if otype in ("success", "correct"):
        return f'CORRECT "{msg}"'
    return None


def _emit_functions(lib: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for func_name, spec in sorted(lib.get("functions", {}).items()):
        if isinstance(spec, dict) and spec.get("code"):
            lines.append(str(spec["code"]))
        else:
            lines.append(f"FUNC: {func_name}")
    return lines


def _emit_goal(goal: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    name = str(goal.get("name") or "unnamed")
    lines.append(f"GOAL: {name}")
    for step in goal.get("steps") or []:
        if isinstance(step, dict):
            lines.extend(_emit_step(step))
    for obj in goal.get("objectives") or []:
        if isinstance(obj, dict):
            row = _emit_objective(obj)
            if row:
                lines.append(row)
    lines.append("")
    return lines


def _emit_goals(lib: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for goal in lib.get("goals", []):
        if isinstance(goal, dict):
            lines.extend(_emit_goal(goal))
    return lines


def library_to_dsl(library: dict[str, Any] | None) -> str:
    """Serialize OQL library JSON back to DSL text."""
    lib = ensure_library_structure(library)
    lines = _emit_functions(lib) + _emit_goals(lib)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")
