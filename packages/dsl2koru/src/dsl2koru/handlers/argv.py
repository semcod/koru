"""Map validated compatibility commands to ``coru.cli`` argv."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from dsl2koru.schema_registry import normalize_verb


def _flag_args(payload: dict[str, Any], key: str, flag: str) -> list[str]:
    """Argv fragment for a boolean ``flag`` enabled by ``payload[key]``."""
    return [flag] if payload.get(key) else []


def _value_args(payload: dict[str, Any], key: str, flag: str) -> list[str]:
    """Argv fragment for ``flag value`` when ``payload[key]`` is set."""
    value = payload.get(key)
    return [flag, str(value)] if value else []


def _positional_args(payload: dict[str, Any], key: str) -> list[str]:
    """Argv fragment with the raw ``payload[key]`` as a positional argument."""
    value = payload.get(key)
    return [str(value)] if value else []


def _build_text_args(payload: dict[str, Any]) -> list[str]:
    target = str(payload.get("target") or "")
    if not target:
        return ["status"]
    return [
        "text",
        target,
        *_flag_args(payload, "llm", "--llm"),
        *_value_args(payload, "shell", "--shell"),
        *_flag_args(payload, "single_action", "--single-action"),
    ]


def _build_chat_args(payload: dict[str, Any]) -> list[str]:
    return [
        "chat",
        *_flag_args(payload, "llm", "--llm"),
        *_value_args(payload, "shell", "--shell"),
        *_flag_args(payload, "single_action", "--single-action"),
    ]


def _build_auto_args(payload: dict[str, Any]) -> list[str]:
    extra_args = payload.get("auto_args")
    if isinstance(extra_args, str):
        extra = extra_args.split()
    else:
        extra = [str(arg) for arg in extra_args or []]
    return ["auto", *_value_args(payload, "shell", "--shell"), *extra]


def _build_ensure_args(payload: dict[str, Any]) -> list[str]:
    return ["ensure", *_flag_args(payload, "install", "--install")]


def _build_lane_args(payload: dict[str, Any]) -> list[str]:
    return [
        "lane-status" if payload.get("lane_status") else "lane",
        *_positional_args(payload, "ide"),
        *_positional_args(payload, "instance"),
    ]


def _build_status_args(payload: dict[str, Any]) -> list[str]:
    return ["status", *_flag_args(payload, "probe", "--probe")]


def _build_doctor_args(payload: dict[str, Any]) -> list[str]:
    return [
        "doctor",
        *_flag_args(payload, "fix", "--fix"),
        *_flag_args(payload, "probe", "--probe"),
        *_value_args(payload, "probe_prompt", "--probe-prompt"),
    ]


_CALIBRATION_SKIP_FLAGS = (
    ("skip_fix", "--skip-fix"),
    ("skip_desktop", "--skip-desktop"),
    ("skip_bridge", "--skip-bridge"),
)


def _build_calibration_args(payload: dict[str, Any]) -> list[str]:
    return [
        "calibration",
        *(flag for key, flag in _CALIBRATION_SKIP_FLAGS if payload.get(key)),
        *_value_args(payload, "probe_prompt", "--probe-prompt"),
    ]


def _build_repair_run_args(payload: dict[str, Any]) -> list[str]:
    return [
        "repair",
        "run",
        *_flag_args(payload, "fix", "--fix"),
        *_positional_args(payload, "ide"),
        *_positional_args(payload, "instance"),
    ]


def _build_repair_history_args(_payload: dict[str, Any]) -> list[str]:
    return ["repair", "history"]


def _build_sync_args(payload: dict[str, Any]) -> list[str]:
    return ["sync", *_flag_args(payload, "all_ides", "--all-ides")]


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
