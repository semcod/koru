"""Packaged planfile ticket templates for Koru queue operators.

Keeps template load/validate/render out of runner.py so Subactor bridge tickets
stay a declarative artifact under templates/planfile/.
"""

from __future__ import annotations

import copy
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any

import yaml

from koru.queue.runners import _DEFAULT_LLM_MODEL
from koru.queue.verify.legacy import VERIFY_COMMAND_HEADS, verify_command_from_criteria

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


def _validate_ticket_files(files: Any) -> list[str]:
    if not isinstance(files, list) or not (1 <= len(files) <= 2):
        return ["ticket.files must list 1–2 placeholder paths"]
    if not all(isinstance(item, str) and item.strip() for item in files):
        return ["ticket.files entries must be non-empty strings"]
    return []


def _validate_ticket_executor(executor: Any) -> list[str]:
    if not isinstance(executor, dict):
        return ["ticket.executor must be a mapping"]
    if str(executor.get("kind") or "").strip().lower() != "llm":
        return ["ticket.executor.kind must be llm"]
    return []


def _validate_required_input_flags(inputs: dict[str, Any]) -> list[str]:
    errors: list[str] = []
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
    return errors


def _validate_max_patch_attempts(inputs: dict[str, Any]) -> list[str]:
    try:
        attempts = int(inputs.get("max_patch_attempts"))
    except (TypeError, ValueError):
        return ["ticket.inputs.max_patch_attempts must be an integer"]
    if attempts < 1 or attempts > 3:
        return ["ticket.inputs.max_patch_attempts must be 1–3"]
    return []


def _validate_verify_command(inputs: dict[str, Any]) -> list[str]:
    verify = str(inputs.get("verify_command") or "").strip()
    if not verify:
        return ["ticket.inputs.verify_command must be non-empty"]
    lowered = verify.lower()
    return [
        f"ticket.inputs.verify_command must not reference {fragment!r}"
        for fragment in _FORBIDDEN_VERIFY_FRAGMENTS
        if fragment in lowered
    ]


def _validate_ticket_inputs(inputs: dict[str, Any]) -> list[str]:
    return [
        *_validate_required_input_flags(inputs),
        *_validate_max_patch_attempts(inputs),
        *_validate_verify_command(inputs),
    ]


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

    errors.extend(_validate_ticket_files(ticket.get("files")))
    errors.extend(_validate_ticket_executor(ticket.get("executor")))

    inputs = ticket.get("inputs")
    if not isinstance(inputs, dict):
        return errors + ["ticket.inputs must be a mapping"]
    errors.extend(_validate_ticket_inputs(inputs))

    forbidden = data.get("forbidden")
    if not isinstance(forbidden, list) or len(forbidden) < 3:
        errors.append("forbidden must list operational boundaries (Plesk/DNS/apply)")

    env = data.get("environment")
    if not isinstance(env, dict) or env.get("KORU_QUEUE_WORKTREE") != "1":
        errors.append("environment.KORU_QUEUE_WORKTREE must be '1'")

    return errors


def _resolve_affected_files(payload: dict[str, Any]) -> tuple[str, str]:
    affected = [str(path) for path in (payload.get("affected_files") or []) if path][:2]
    fallback_files = (
        "orchestrator/bin/subactor-run.mjs",
        "orchestrator/tests/development-defect.test.mjs",
    )
    while len(affected) < 2:
        affected.append(fallback_files[len(affected)])
    return affected[0], affected[1]


def _build_prompt_body(payload: dict[str, Any]) -> str:
    acceptance = [str(item) for item in (payload.get("acceptance_tests") or []) if item]
    prompt_lines = [f"- Acceptance: {item}" for item in acceptance[:5]]
    message = str(payload.get("message") or "").strip()
    if message:
        prompt_lines.insert(0, message[:500])
    return "\n".join(prompt_lines) if prompt_lines else "Add focused regression coverage."


def variables_from_development_defect(payload: dict[str, Any]) -> dict[str, str]:
    """Map Subactor orchestrator ``development_defect`` payload to template vars."""
    file_1, file_2 = _resolve_affected_files(payload)
    return {
        "COMPONENT": str(payload.get("component") or "unknown"),
        "ERROR_CODE": str(payload.get("error_code") or "unknown"),
        "FINGERPRINT": str(payload.get("fingerprint") or ""),
        "DISCOVERED_IN": str(
            payload.get("discovered_in") or payload.get("source_ticket_id") or "",
        ),
        "FILE_1": file_1,
        "FILE_2": file_2,
        "PROMPT_BODY": _build_prompt_body(payload),
    }


def resolve_repair_llm_model(variables: dict[str, str] | None = None) -> str:
    """Pick the model for ``executor.kind=llm`` repair tickets."""
    merged = variables or {}
    for candidate in (merged.get("LLM_MODEL"), os.environ.get("LLM_MODEL")):
        model = str(candidate or "").strip()
        if model:
            return model
    return _DEFAULT_LLM_MODEL




def _resolve_hydrated_inputs(
    ticket: dict[str, Any], template_inputs: dict[str, Any]
) -> dict[str, Any]:
    inputs = dict(ticket.get("inputs") or {})
    for key in ("patch_mode", "promotion_mode", "worktree", "max_patch_attempts"):
        if key not in inputs and key in template_inputs:
            inputs[key] = template_inputs[key]

    # verify_command is resolved separately, with the template last. Its value
    # there is a documentation example naming a Subactor path, and planfile
    # strips the ticket's own key on import — so seeding from the template first
    # let that example outrank the command the ticket actually declared. A gate
    # naming a file the project does not have fails every patch put through it.
    if not str(inputs.get("verify_command") or "").strip():
        from_criteria = verify_command_from_criteria(ticket)
        if from_criteria:
            inputs["verify_command"] = from_criteria
        elif "verify_command" in template_inputs:
            inputs["verify_command"] = template_inputs["verify_command"]
    if not str(inputs.get("llm_model") or "").strip():
        inputs["llm_model"] = resolve_repair_llm_model()
    return inputs


def hydrate_subactor_repair_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
    """Restore Koru patch policy when planfile import drops unknown ``inputs`` keys."""
    labels = {str(label).lower() for label in (ticket.get("labels") or [])}
    if "source:subactor-bridge" not in labels:
        return ticket

    template = load_ticket_template(SUBACTOR_DEVELOPMENT_REPAIR)
    template_ticket = template["ticket"]
    template_inputs = template_ticket.get("inputs") or {}
    out = dict(ticket)
    out["inputs"] = _resolve_hydrated_inputs(ticket, template_inputs)

    executor = out.get("executor") or {}
    if not str(executor.get("kind") or "").strip():
        out["executor"] = dict(template_ticket.get("executor") or {"kind": "llm", "mode": "automatic"})

    template_env = template.get("environment") or {}
    for key, value in template_env.items():
        os.environ.setdefault(str(key), str(value))
    return out


def hydrate_todo2code_ticket(ticket: dict[str, Any], project: Path) -> dict[str, Any]:
    """Restore the autonomous contract that older planfile schemas discard."""
    labels = [str(label) for label in (ticket.get("labels") or [])]
    lowered = {label.lower() for label in labels}
    source = ticket.get("source") if isinstance(ticket.get("source"), dict) else {}
    source_tool = str(source.get("tool") or "").lower()
    if "todo2code" not in lowered and "todo2code" not in source_tool:
        return ticket

    out = dict(ticket)
    inputs = dict(ticket.get("inputs") or {})
    execution = ticket.get("execution") if isinstance(ticket.get("execution"), dict) else {}
    try:
        attempt = int(execution.get("attempt") or 0)
    except (TypeError, ValueError):
        attempt = 0

    primary = os.environ.get(
        "KORU_TODO2CODE_LLM_MODEL",
        "openrouter/anthropic/claude-opus-5",
    )
    fallback = os.environ.get(
        "KORU_TODO2CODE_LLM_FALLBACK_MODEL",
        "openrouter/qwen/qwen3-coder-next",
    )
    inputs["llm_model"] = fallback if attempt > 0 else str(inputs.get("llm_model") or primary)
    inputs.setdefault("llm_max_tokens", int(os.environ.get("KORU_TODO2CODE_LLM_MAX_TOKENS", "4000")))
    inputs.setdefault("llm_timeout_seconds", 300)
    inputs.setdefault("include_project_context", True)
    inputs.setdefault("context_files", list(ticket.get("files") or [])[:12])
    inputs["expect_files_changed"] = True
    inputs["patch_mode"] = True
    inputs.setdefault("promotion_mode", "branch")
    inputs.setdefault("worktree", True)
    inputs.setdefault("max_patch_attempts", 3)
    inputs.setdefault("risk_class", "R1")
    from koru.autonomy.todo2code_discovery import _config_value

    contract = str(
        inputs.get("contract")
        or _config_value("KORU_TODO2CODE_CONTRACT", project)
        or ""
    ).strip()
    if contract:
        inputs["contract"] = contract

    executor = out.get("executor") if isinstance(out.get("executor"), dict) else {}
    if str(executor.get("kind") or "human").lower() == "llm" and not contract:
        # Older imported tickets may already say llm/automatic. Do not let a
        # lossy Planfile round-trip turn that historical value into authority:
        # autonomous todo2code patches require a target-owned capability contract.
        out["executor"] = {"kind": "human", "mode": "interactive"}
        inputs["governance_block_reason"] = (
            "todo2code LLM execution requires KORU_TODO2CODE_CONTRACT"
        )

    context = source.get("context") if isinstance(source.get("context"), dict) else {}
    diagnostic_ids = [
        str(value) for value in (context.get("diagnostic_ids") or [])
        if re.fullmatch(r"DIAG-[a-f0-9]+", str(value))
    ]
    if not str(inputs.get("verify_command") or "").strip() and diagnostic_ids:
        from koru.autonomy.todo2code_discovery import _t2c_executable

        t2c = _t2c_executable(project)
        if t2c:
            # Verification runs in a temporary worktree of the target project.
            # A relative developer PYTHONPATH (commonly ``src``) would then
            # resolve against that project and make the Koru gate disappear.
            koru_source_root = str(Path(__file__).resolve().parents[2])
            command = [
                "env",
                f"PYTHONPATH={koru_source_root}",
                sys.executable,
                "-m",
                "koru.queue.todo2code_gate",
                "--project",
                ".",
                "--t2c",
                t2c,
            ]
            for diagnostic_id in diagnostic_ids:
                command.extend(["--diagnostic", diagnostic_id])
            inputs["verify_command"] = shlex.join(command)

    if "type:development-defect" not in lowered:
        labels.append("type:development-defect")
    out["labels"] = list(dict.fromkeys(labels))
    out["inputs"] = inputs
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
    if acceptance and acceptance[0].split()[0] in VERIFY_COMMAND_HEADS:
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
