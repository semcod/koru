"""CLI argument normalization helpers for ``koru autonomous``."""

from __future__ import annotations

import os
from typing import Any


def _truthy_strategy_value(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _strategy_float(value: Any) -> float | None:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _strategy_tools_enabled(strategy: dict[str, Any]) -> bool:
    idle = strategy.get("idle_discovery")
    if not isinstance(idle, dict):
        return True
    tools = idle.get("tools")
    if not isinstance(tools, dict):
        return True
    automated = {
        str(item).strip()
        for item in (tools.get("automated") or [])
        if str(item).strip()
    }
    artifact_sources = {
        str(item).strip()
        for item in (tools.get("artifact_sources") or [])
        if str(item).strip()
    }
    return bool(automated.intersection({"code2llm", "koru_scan"}) or artifact_sources)


def _openrouter_model_from_strategy(strategy: dict[str, Any]) -> str:
    planning = strategy.get("planning_assistant")
    if not isinstance(planning, dict):
        return ""
    openrouter = planning.get("openrouter")
    if not isinstance(openrouter, dict):
        return ""
    model = str(openrouter.get("model") or "").strip()
    return model.removeprefix("openrouter/") if model else ""


def apply_autonomy_strategy_defaults(args: Any) -> None:
    """Apply ``koru.yaml`` autonomy.strategy as runtime defaults for ``koru auto``.

    Explicit CLI flags still win. The strategy file is meant to describe the
    workflow, so these defaults make that contract operational without taking
    control away from one-off command invocations.
    """
    if not getattr(args, "_invoked_as_auto", False) or getattr(args, "action", "") != "up":
        return
    try:
        from koru.autonomy_strategy import load_autonomy_strategy

        strategy = load_autonomy_strategy(args.project)
    except Exception:  # noqa: BLE001 - strategy loading is advisory
        return
    if not isinstance(strategy, dict):
        return

    user_options = getattr(args, "_auto_user_options", set()) or set()
    _apply_idle_discovery_strategy_defaults(args, strategy, user_options)
    _apply_planning_assistant_strategy_defaults(strategy)


def _apply_idle_discovery_strategy_defaults(args: Any, strategy: dict, user_options: set[str]) -> bool:
    idle = strategy.get("idle_discovery")
    idle_enabled = True
    if isinstance(idle, dict):
        idle_enabled = _truthy_strategy_value(idle.get("enabled"), True)
        min_interval = _strategy_float(idle.get("min_interval_seconds"))
        if min_interval is not None and "--scan-after-idle-min-interval" not in user_options:
            args.scan_after_idle_min_interval = min_interval

    if not user_options.intersection({"--scan-after-idle-queue", "--no-scan-after-idle-queue"}):
        args.scan_after_idle_queue = idle_enabled
    if not user_options.intersection({"--semcod-artifacts", "--no-semcod-artifacts"}):
        args.semcod_artifacts = idle_enabled and _strategy_tools_enabled(strategy)
    return idle_enabled


def _apply_planning_assistant_strategy_defaults(strategy: dict) -> None:
    planning = strategy.get("planning_assistant")
    if isinstance(planning, dict):
        enabled = _truthy_strategy_value(planning.get("enabled"), True)
        os.environ.setdefault("KORU_PLANNING_LLM", "1" if enabled else "0")
        model = _openrouter_model_from_strategy(strategy)
        if model:
            os.environ.setdefault("KORU_PLANNING_LLM_MODEL", model)


def normalize_autonomous_argv(argv: list[str]) -> list[str]:
    """Normalize command line arguments for autonomous mode."""
    if not argv:
        return ["up"]
    if argv[0] == "safe-up":
        return [
            "up",
            "--ticket-sources",
            "queue",
            "--idle-diagnostics",
            "quick",
            "--diagnostic-tickets",
            "--autopilot-action",
            "off",
            "--no-autopilot",
            "--max-cycles",
            "1",
            "--no-semcod-artifacts",
            *argv[1:],
        ]
    if argv[0] != "up" and argv[0] not in ("-h", "--help"):
        return ["up", *argv]
    return argv


def configure_auto_mode_args(
    argv: list[str],
    invoked_as_auto: bool,
    *,
    collect_argv_options: Any,
    expand_auto_up_defaults: Any,
) -> tuple[set[str], list[str]]:
    """Configure arguments for auto mode and return user options and normalized argv."""
    auto_user_options: set[str] = set()
    if invoked_as_auto and argv and argv[0] == "up":
        auto_user_options = collect_argv_options(argv[1:])
        argv = expand_auto_up_defaults(argv)
    return auto_user_options, argv


def apply_auto_pipeline_flags(args: Any, invoked_as_auto: bool) -> None:
    """Apply auto-pipeline specific flags to args."""
    args._auto_pipeline_enabled = (
        invoked_as_auto
        and args.action == "up"
        and os.environ.get("KORU_AUTO_PIPELINE", "").strip().lower()
        in {"1", "true", "yes", "on"}
    )


def apply_replace_existing_flags(args: Any, invoked_as_auto: bool) -> None:
    """Apply replace-existing flags for auto mode."""
    if invoked_as_auto:
        args.replace_existing_global = True
        if not args.allow_duplicate and not args.replace_existing:
            args.replace_existing = True
    elif not hasattr(args, "replace_existing_global"):
        args.replace_existing_global = False


__all__ = [
    "apply_autonomy_strategy_defaults",
    "normalize_autonomous_argv",
    "configure_auto_mode_args",
    "apply_auto_pipeline_flags",
    "apply_replace_existing_flags",
]
