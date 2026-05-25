"""Schemas and validation for declarative IDE command scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from koruide.command_catalog import build_ide_command_catalog, supported_catalog_ides

SCENARIO_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://semcod.dev/schemas/koru/ide-command-scenario.v1.json",
    "title": "Koru IDE command scenario",
    "type": "object",
    "additionalProperties": False,
    "required": ["ide", "steps"],
    "properties": {
        "schema": {
            "type": "string",
            "const": "koru.ide_command_scenario.v1",
            "description": "Optional explicit schema marker.",
        },
        "name": {"type": "string"},
        "description": {"type": "string"},
        "ide": {
            "type": "string",
            "enum": list(supported_catalog_ides()),
        },
        "mode": {
            "type": "string",
            "enum": ["plan", "dry_run", "execute"],
            "default": "plan",
            "description": (
                "Only plan/dry_run are schema-level safe; execution is a Koru policy "
                "decision."
            ),
        },
        "requires_runtime_verification": {
            "type": "boolean",
            "default": True,
        },
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["action"],
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "focus_open",
                            "focus_input",
                            "paste_text",
                            "submit",
                            "atomic_send",
                            "reload_reconnect",
                            "diagnostics",
                            "wait",
                        ],
                    },
                    "command": {"type": "string"},
                    "args": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                    "expect": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                    "risk_override_reason": {"type": "string"},
                    "optional": {"type": "boolean", "default": False},
                    "timeout_seconds": {"type": "number", "minimum": 0},
                    "notes": {"type": "string"},
                },
            },
        },
    },
}

SAFE_EXECUTION_RISKS = frozenset({"low", "medium"})


@dataclass(frozen=True)
class ScenarioValidation:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    normalized: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "normalized": self.normalized,
        }


def ide_command_scenario_schema() -> dict[str, Any]:
    return SCENARIO_SCHEMA


def validate_ide_command_scenario(raw: dict[str, Any]) -> ScenarioValidation:
    """Validate a scenario against Koru's static command catalog.

    This does not prove that the active IDE currently exports a command. The
    plugin still has to perform runtime verification before any real execution.
    """
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(raw, dict):
        return ScenarioValidation(
            ok=False,
            errors=("scenario must be an object",),
            warnings=(),
            normalized={},
        )

    ide = str(raw.get("ide") or "").strip().lower()
    if ide not in supported_catalog_ides():
        errors.append(f"unknown ide {ide!r}; supported: {', '.join(supported_catalog_ides())}")
        ide = ide or "unknown"

    steps = raw.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be a non-empty array")
        steps = []

    catalog_rows = _rows_by_command(ide) if ide in supported_catalog_ides() else {}
    normalized_steps: list[dict[str, Any]] = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f"steps[{index}] must be an object")
            continue
        action = str(step.get("action") or "").strip()
        if not action:
            errors.append(f"steps[{index}].action is required")
            continue
        command = str(step.get("command") or "").strip()
        row = catalog_rows.get(command) if command else None
        if action not in _allowed_actions():
            errors.append(f"steps[{index}].action {action!r} is not allowed")
        if action not in {"wait", "diagnostics"} and not command:
            errors.append(f"steps[{index}].command is required for action {action!r}")
        if command and row is None:
            warnings.append(f"steps[{index}].command {command!r} is not in catalog for {ide}")
        if row is not None and row["category"] != action:
            warnings.append(
                f"steps[{index}].command {command!r} is category {row['category']!r}, "
                f"not action {action!r}",
            )
        if row is not None and row["risk"] not in SAFE_EXECUTION_RISKS:
            reason = str(step.get("risk_override_reason") or "").strip()
            if reason:
                warnings.append(
                    f"steps[{index}].command {command!r} is high risk; override recorded",
                )
            else:
                errors.append(
                    f"steps[{index}].command {command!r} is high risk and needs "
                    "risk_override_reason",
                )
        normalized_steps.append(
            {
                "action": action,
                **({"command": command} if command else {}),
                **({"args": step.get("args")} if isinstance(step.get("args"), dict) else {}),
                **({"expect": step.get("expect")} if isinstance(step.get("expect"), dict) else {}),
                **({"optional": bool(step.get("optional"))} if "optional" in step else {}),
                **(
                    {"timeout_seconds": step.get("timeout_seconds")}
                    if "timeout_seconds" in step
                    else {}
                ),
                **(
                    {"risk_override_reason": str(step.get("risk_override_reason"))}
                    if step.get("risk_override_reason")
                    else {}
                ),
                **({"notes": str(step.get("notes"))} if step.get("notes") else {}),
            },
        )

    normalized = {
        "schema": "koru.ide_command_scenario.v1",
        "ide": ide,
        "mode": str(raw.get("mode") or "plan"),
        "requires_runtime_verification": bool(raw.get("requires_runtime_verification", True)),
        "steps": normalized_steps,
        **({"name": str(raw.get("name"))} if raw.get("name") else {}),
        **({"description": str(raw.get("description"))} if raw.get("description") else {}),
    }
    mode = normalized["mode"]
    if mode not in {"plan", "dry_run", "execute"}:
        errors.append(f"mode {mode!r} is not allowed")
    if mode == "execute":
        warnings.append(
            "execute mode still requires runtime command verification and Koru policy approval",
        )
    return ScenarioValidation(
        ok=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        normalized=normalized,
    )


def llm_scenario_prompt(ide: str | None = None) -> str:
    catalog = build_ide_command_catalog(ide)
    schema_json = json.dumps(SCENARIO_SCHEMA, indent=2, sort_keys=True)
    catalog_json = json.dumps(catalog, indent=2, sort_keys=True)
    return (
        "Write a Koru IDE command scenario as JSON matching "
        "`koru.ide_command_scenario.v1`.\n"
        "Rules: choose low-risk commands first, include `risk_override_reason` for any "
        "high-risk command, keep `requires_runtime_verification: true`, and do not invent "
        "commands outside the catalog unless you mark the step optional with notes.\n\n"
        "Scenario JSON Schema:\n"
        f"{schema_json}\n\n"
        "Command catalog:\n"
        f"{catalog_json}\n"
    )


def _rows_by_command(ide: str) -> dict[str, dict[str, Any]]:
    catalog = build_ide_command_catalog(ide)
    rows = catalog["ides"][ide]["commands"]
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        previous = by_id.get(row["id"])
        if previous is None or _risk_rank(row["risk"]) > _risk_rank(previous["risk"]):
            by_id[row["id"]] = row
    return by_id


def _risk_rank(risk: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(risk, 2)


def _allowed_actions() -> frozenset[str]:
    return frozenset(
        {
            "focus_open",
            "focus_input",
            "paste_text",
            "submit",
            "atomic_send",
            "reload_reconnect",
            "diagnostics",
            "wait",
        },
    )


__all__ = [
    "SCENARIO_SCHEMA",
    "ScenarioValidation",
    "ide_command_scenario_schema",
    "llm_scenario_prompt",
    "validate_ide_command_scenario",
]
