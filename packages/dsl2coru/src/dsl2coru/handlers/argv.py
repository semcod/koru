"""Map validated command dicts to coru.cli argv."""

from __future__ import annotations

from typing import Any

from dsl2coru.schema_registry import normalize_verb


def _build_text_args(payload: dict[str, Any]) -> list[str]:
    target = str(payload.get("target") or "")
    if not target:
        return ["status"]
    command = ["text", target]
    if payload.get("llm"):
        command.append("--llm")
    if shell := payload.get("shell"):
        command.extend(["--shell", str(shell)])
    if payload.get("single_action"):
        command.append("--single-action")
    return command


def _build_chat_args(payload: dict[str, Any]) -> list[str]:
    command = ["chat"]
    if payload.get("llm"):
        command.append("--llm")
    if shell := payload.get("shell"):
        command.extend(["--shell", str(shell)])
    if payload.get("single_action"):
        command.append("--single-action")
    return command


def _build_auto_args(payload: dict[str, Any]) -> list[str]:
    command = ["auto"]
    if shell := payload.get("shell"):
        command.extend(["--shell", str(shell)])
    if command_args := payload.get("auto_args"):
        if isinstance(command_args, str):
            command.extend(command_args.split())
        else:
            command.extend([str(item) for item in command_args])
    return command


def _build_ensure_args(payload: dict[str, Any]) -> list[str]:
    command = ["ensure"]
    if payload.get("install"):
        command.append("--install")
    return command


def _build_lane_args(payload: dict[str, Any]) -> list[str]:
    command = ["lane-status" if payload.get("lane_status") else "lane"]
    if ide := payload.get("ide"):
        command.append(str(ide))
    if instance := payload.get("instance"):
        command.append(str(instance))
    return command


def _build_status_args(payload: dict[str, Any]) -> list[str]:
    command = ["status"]
    if payload.get("probe"):
        command.append("--probe")
    return command


def _build_doctor_args(payload: dict[str, Any]) -> list[str]:
    command = ["doctor"]
    if payload.get("fix"):
        command.append("--fix")
    if payload.get("probe"):
        command.append("--probe")
    if probe_prompt := payload.get("probe_prompt"):
        command.extend(["--probe-prompt", str(probe_prompt)])
    return command


def _build_calibration_args(payload: dict[str, Any]) -> list[str]:
    command = ["calibration"]
    if payload.get("skip_fix"):
        command.append("--skip-fix")
    if payload.get("skip_desktop"):
        command.append("--skip-desktop")
    if payload.get("skip_bridge"):
        command.append("--skip-bridge")
    if probe_prompt := payload.get("probe_prompt"):
        command.extend(["--probe-prompt", str(probe_prompt)])
    return command


def _build_repair_run_args(payload: dict[str, Any]) -> list[str]:
    command = ["repair", "run"]
    if payload.get("fix"):
        command.append("--fix")
    if ide := payload.get("ide"):
        command.append(str(ide))
    if instance := payload.get("instance"):
        command.append(str(instance))
    return command


def _build_repair_history_args(_payload: dict[str, Any]) -> list[str]:
    return ["repair", "history"]


def _build_sync_args(payload: dict[str, Any]) -> list[str]:
    command = ["sync"]
    if payload.get("all_ides"):
        command.append("--all-ides")
    return command


def _build_env_args(payload: dict[str, Any]) -> list[str]:
    default_file = str(payload.get("file") or payload.get("default_file") or "")
    if default_file:
        return ["env", "--file", default_file]
    return ["env"]


def _build_query_args(payload: dict[str, Any]) -> list[str]:
    target = str(payload.get("target") or "")
    if not target:
        return ["status"]
    lowered = target.lower().strip()
    if lowered in {"status", "diagnose"}:
        return ["status"]
    if lowered in {"lane", "lane-status"}:
        return ["lane"]
    if lowered in {"auto", "autonomous"}:
        return ["auto"]
    return ["status"]


_ARG_BUILDERS: dict[str, Any] = {
    "TEXT": _build_text_args,
    "CHAT": _build_chat_args,
    "AUTO": _build_auto_args,
    "ENSURE": _build_ensure_args,
    "LANE": _build_lane_args,
    "STATUS": _build_status_args,
    "DOCTOR": _build_doctor_args,
    "CALIBRATION": _build_calibration_args,
    "REPAIR_RUN": _build_repair_run_args,
    "REPAIR_HISTORY": _build_repair_history_args,
    "SYNC": _build_sync_args,
    "ENV": _build_env_args,
    "QUERY": _build_query_args,
}


def to_cli_args(payload: dict[str, Any]) -> list[str]:
    verb = normalize_verb(str(payload.get("verb", "")))
    builder = _ARG_BUILDERS.get(verb)
    if builder:
        return builder(payload)
    target = str(payload.get("target") or "")
    return ["text", verb + (f" {target}" if target else "")]
