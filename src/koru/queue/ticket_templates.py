"""Packaged planfile ticket templates for Koru queue operators.

Keeps template load/validate/render out of runner.py so Subactor bridge tickets
stay a declarative artifact under templates/planfile/.
"""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any

import yaml

from koru.queue.runners import _DEFAULT_LLM_MODEL

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

_VERIFY_COMMAND_PREFIXES: frozenset[str] = frozenset(
    {"node", "npm", "pytest", "python", "python3", "bash"},
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

    executor = ticket.get("executor")
    if not isinstance(executor, dict):
        errors.append("ticket.executor must be a mapping")
    elif str(executor.get("kind") or "").strip().lower() != "llm":
        errors.append("ticket.executor.kind must be llm")

    inputs = ticket.get("inputs")
    if not isinstance(inputs, dict):
        return errors + ["ticket.inputs must be a mapping"]
    llm_model = str(inputs.get("llm_model") or "").strip()
    if not llm_model:
        errors.append("ticket.inputs.llm_model must be non-empty")
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


def variables_from_development_defect(payload: dict[str, Any]) -> dict[str, str]:
    """Map Subactor orchestrator ``development_defect`` payload to template vars."""
    affected = [str(path) for path in (payload.get("affected_files") or []) if path][:2]
    fallback_files = (
        "orchestrator/bin/subactor-run.mjs",
        "orchestrator/tests/development-defect.test.mjs",
    )
    while len(affected) < 2:
        affected.append(fallback_files[len(affected)])

    acceptance = [str(item) for item in (payload.get("acceptance_tests") or []) if item]
    prompt_lines = [f"- Acceptance: {item}" for item in acceptance[:5]]
    message = str(payload.get("message") or "").strip()
    if message:
        prompt_lines.insert(0, message[:500])

    return {
        "COMPONENT": str(payload.get("component") or "unknown"),
        "ERROR_CODE": str(payload.get("error_code") or "unknown"),
        "FINGERPRINT": str(payload.get("fingerprint") or ""),
        "DISCOVERED_IN": str(
            payload.get("discovered_in") or payload.get("source_ticket_id") or "",
        ),
        "FILE_1": affected[0],
        "FILE_2": affected[1],
        "PROMPT_BODY": "\n".join(prompt_lines) if prompt_lines else "Add focused regression coverage.",
    }


def resolve_repair_llm_model(variables: dict[str, str] | None = None) -> str:
    """Pick the model for ``executor.kind=llm`` repair tickets."""
    merged = variables or {}
    for candidate in (merged.get("LLM_MODEL"), os.environ.get("LLM_MODEL")):
        model = str(candidate or "").strip()
        if model:
            return model
    return _DEFAULT_LLM_MODEL


def _verify_from_acceptance_criteria(ticket: dict[str, Any]) -> str:
    for item in ticket.get("acceptance_criteria") or []:
        cmd = str(item or "").strip()
        if cmd and cmd.split()[0] in _VERIFY_COMMAND_PREFIXES:
            return cmd
    return ""


def hydrate_subactor_repair_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    """Restore Koru patch policy when planfile import drops unknown ``inputs`` keys."""
    labels = {str(label).lower() for label in (ticket.get("labels") or [])}
    if "source:subactor-bridge" not in labels:
        return ticket

    template = load_ticket_template(SUBACTOR_DEVELOPMENT_REPAIR)
    template_ticket = template["ticket"]
    template_inputs = template_ticket.get("inputs") or {}
    out = dict(ticket)
    inputs = dict(out.get("inputs") or {})

    for key in ("patch_mode", "promotion_mode", "worktree", "max_patch_attempts", "verify_command"):
        if key not in inputs and key in template_inputs:
            inputs[key] = template_inputs[key]
    if not str(inputs.get("verify_command") or "").strip():
        from_criteria = _verify_from_acceptance_criteria(out)
        if from_criteria:
            inputs["verify_command"] = from_criteria
    if not str(inputs.get("llm_model") or "").strip():
        inputs["llm_model"] = resolve_repair_llm_model()

    out["inputs"] = inputs
    executor = out.get("executor") or {}
    if not str(executor.get("kind") or "").strip():
        out["executor"] = dict(template_ticket.get("executor") or {"kind": "llm", "mode": "automatic"})

    template_env = template.get("environment") or {}
    for key, value in template_env.items():
        os.environ.setdefault(str(key), str(value))
    return out


def render_subactor_repair_ticket(variables: dict[str, str]) -> dict[str, Any]:
    """Render the Subactor repair skeleton with concrete bridge metadata."""
    data = load_ticket_template(SUBACTOR_DEVELOPMENT_REPAIR)
    errors = validate_subactor_repair_template(data)
    if errors:
        raise ValueError("; ".join(errors))

    render_vars = dict(variables)
    render_vars.setdefault("LLM_MODEL", resolve_repair_llm_model(render_vars))
    rendered = _substitute(copy.deepcopy(data["ticket"]), render_vars)
    rendered["inputs"]["llm_model"] = resolve_repair_llm_model(render_vars)
    verify = str(rendered.get("inputs", {}).get("verify_command") or "").strip()
    if verify:
        rendered["acceptance_criteria"] = [verify]
    leftover = _PLACEHOLDER_RE.findall(yaml.safe_dump(rendered))
    if leftover:
        missing = ", ".join(sorted(set(leftover)))
        raise ValueError(f"unresolved template placeholders: {missing}")
    return rendered


def render_repair_ticket_from_development_defect(payload: dict[str, Any]) -> dict[str, Any]:
    """Render Koru repair ticket from a Subactor bridge ``development_defect`` payload."""
    classification = payload.get("classification") or {}
    if classification.get("action") != "ticket":
        reason = classification.get("reason") or classification.get("category") or "operational"
        raise ValueError(f"payload is not a development ticket candidate: {reason}")

    rendered = render_subactor_repair_ticket(variables_from_development_defect(payload))
    acceptance = [str(item).strip() for item in (payload.get("acceptance_tests") or []) if item]
    if acceptance and acceptance[0].split()[0] in _VERIFY_COMMAND_PREFIXES:
        rendered.setdefault("inputs", {})["verify_command"] = acceptance[0]
        rendered["acceptance_criteria"] = [acceptance[0]]
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
