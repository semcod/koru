"""Packaged planfile ticket templates for Koru queue operators.

Keeps template load/validate/render out of runner.py so Subactor bridge tickets
stay a declarative artifact under templates/planfile/.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import yaml

SUBACTOR_DEVELOPMENT_REPAIR = "subactor-development-repair"
_TEMPLATE_SCHEMA = "koru.queue.ticket_template/v1"
_PLACEHOLDER_RE = re.compile(r"__([A-Z0-9_]+)__")

_REQUIRED_INPUTS: tuple[str, ...] = (
    "patch_mode",
    "promotion_mode",
    "worktree",
    "max_patch_attempts",
    "verify_command",
)

_FORBIDDEN_VERIFY_FRAGMENTS: tuple[str, ...] = (
    "plesk",
    "--apply",
    "dns",
    "connector-lan",
    "subactor ask",
    "sftp",
)


def template_dir() -> Path:
    """Directory holding packaged *.yaml.template queue tickets."""
    return Path(__file__).resolve().parents[3] / "templates" / "planfile"


def template_path(name: str) -> Path:
    return template_dir() / f"{name}.yaml.template"


def load_ticket_template(name: str) -> dict[str, Any]:
    path = template_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"ticket template not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"template must be a mapping: {path}")
    return data


def validate_subactor_repair_template(data: dict[str, Any]) -> list[str]:
    """Return validation errors; empty list means the template schema is sound."""
    errors: list[str] = []
    if data.get("schema") != _TEMPLATE_SCHEMA:
        errors.append(f"schema must be {_TEMPLATE_SCHEMA!r}")
    if data.get("id") != SUBACTOR_DEVELOPMENT_REPAIR:
        errors.append(f"id must be {SUBACTOR_DEVELOPMENT_REPAIR!r}")

    ticket = data.get("ticket")
    if not isinstance(ticket, dict):
        return errors + ["ticket must be a mapping"]

    files = ticket.get("files")
    if not isinstance(files, list) or not (1 <= len(files) <= 2):
        errors.append("ticket.files must list 1–2 placeholder paths")
    elif not all(isinstance(item, str) and item.strip() for item in files):
        errors.append("ticket.files entries must be non-empty strings")

    inputs = ticket.get("inputs")
    if not isinstance(inputs, dict):
        return errors + ["ticket.inputs must be a mapping"]
    for key in _REQUIRED_INPUTS:
        if key not in inputs:
            errors.append(f"ticket.inputs.{key} is required")

    if inputs.get("patch_mode") is not True:
        errors.append("ticket.inputs.patch_mode must be true")
    if str(inputs.get("promotion_mode") or "").strip().lower() != "branch":
        errors.append("ticket.inputs.promotion_mode must be branch")
    if inputs.get("worktree") is not True:
        errors.append("ticket.inputs.worktree must be true")

    try:
        attempts = int(inputs.get("max_patch_attempts"))
    except (TypeError, ValueError):
        errors.append("ticket.inputs.max_patch_attempts must be an integer")
    else:
        if attempts < 1 or attempts > 3:
            errors.append("ticket.inputs.max_patch_attempts must be 1–3")

    verify = str(inputs.get("verify_command") or "").strip()
    if not verify:
        errors.append("ticket.inputs.verify_command must be non-empty")
    else:
        lowered = verify.lower()
        for fragment in _FORBIDDEN_VERIFY_FRAGMENTS:
            if fragment in lowered:
                errors.append(
                    f"ticket.inputs.verify_command must not reference {fragment!r}"
                )

    forbidden = data.get("forbidden")
    if not isinstance(forbidden, list) or len(forbidden) < 3:
        errors.append("forbidden must list operational boundaries (Plesk/DNS/apply)")

    env = data.get("environment")
    if not isinstance(env, dict) or env.get("KORU_QUEUE_WORKTREE") != "1":
        errors.append("environment.KORU_QUEUE_WORKTREE must be '1'")

    return errors


def render_subactor_repair_ticket(variables: dict[str, str]) -> dict[str, Any]:
    """Render the Subactor repair skeleton with concrete bridge metadata."""
    data = load_ticket_template(SUBACTOR_DEVELOPMENT_REPAIR)
    errors = validate_subactor_repair_template(data)
    if errors:
        raise ValueError("; ".join(errors))

    rendered = _substitute(copy.deepcopy(data["ticket"]), variables)
    leftover = _PLACEHOLDER_RE.findall(yaml.safe_dump(rendered))
    if leftover:
        missing = ", ".join(sorted(set(leftover)))
        raise ValueError(f"unresolved template placeholders: {missing}")
    return rendered


def _substitute(value: Any, variables: dict[str, str]) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in variables:
                return match.group(0)
            return variables[key]

        return _PLACEHOLDER_RE.sub(repl, value)
    if isinstance(value, list):
        return [_substitute(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, variables) for key, item in value.items()}
    return value
