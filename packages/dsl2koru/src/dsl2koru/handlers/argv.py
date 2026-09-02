"""Map validated compatibility commands to ``coru.cli`` argv."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from dsl2koru.schema_registry import normalize_verb


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
        command.extend(command_args.split() if isinstance(command_args, str) else map(str, command_args))
    return command


def _build_ensure_args(payload: dict[str, Any]) -> list[str]:
    return ["ensure", *(["--install"] if payload.get("install") else [])]


def _build_lane_args(payload: dict[str, Any]) -> list[str]:
    command = ["lane-status" if payload.get("lane_status") else "lane"]
    if ide := payload.get("ide"):
        command.append(str(ide))
    if instance := payload.get("instance"):
        command.append(str(instance))
    return command


def _build_status_args(payload: dict[str, Any]) -> list[str]:
    return ["status", *(["--probe"] if payload.get("probe") else [])]


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
    for key, flag in (
        ("skip_fix", "--skip-fix"),
        ("skip_desktop", "--skip-desktop"),
        ("skip_bridge", "--skip-bridge"),
    ):
        if payload.get(key):
            command.append(flag)
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
    return ["sync", *(["--all-ides"] if payload.get("all_ides") else [])]


def _build_env_args(payload: dict[str, Any]) -> list[str]:
    default_file = str(payload.get("file") or payload.get("default_file") or "")
    return ["env", "--file", default_file] if default_file else ["env"]


def _build_query_args(payload: dict[str, Any]) -> list[str]:
    target = str(payload.get("target") or "").lower().strip()
    if target in {"lane", "lane-status"}:
        return ["lane"]
    if target in {"auto", "autonomous"}:
        return ["auto"]
    return ["status"]


_ARG_BUILDERS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
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
    if builder := _ARG_BUILDERS.get(verb):
        return builder(payload)
    target = str(payload.get("target") or "")
    return ["text", verb + (f" {target}" if target else "")]
