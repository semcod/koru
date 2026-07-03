"""Argument parser and subcommand registration helpers extracted from cli.py.

Contains ``_build_parser`` and all ``_register_*`` / ``_add_*`` helpers so that
``cli.py`` is not responsible for the argparse wiring detail.
"""
from __future__ import annotations

import argparse
from typing import Any

from coru.cli_calibration import _register_calibration_command


def _add_lane_identifiers(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("ide", nargs="?")
    parser.add_argument("instance", nargs="?")


def _add_shell_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--shell", choices=("bash", "sh", "zsh", "powershell"), default="bash")


def _register_lane_commands(sub: Any) -> None:
    p_lane = sub.add_parser("lane", help="emit lane environment exports")
    _add_lane_identifiers(p_lane)
    _add_shell_argument(p_lane)
    p_lane.add_argument("--print-env", action="store_true", help="deprecated alias; env is always printed")

    p_status = sub.add_parser("lane-status", help="show lane status")
    _add_lane_identifiers(p_status)

    p_status_alias = sub.add_parser("status", help="orchestrated lane diagnostics (env, daemon, status)")
    _add_lane_identifiers(p_status_alias)
    p_status_alias.add_argument("--probe", action="store_true", help="run plugin-required drive probe")

    p_env_alias = sub.add_parser("env", help="alias for lane")
    _add_lane_identifiers(p_env_alias)
    _add_shell_argument(p_env_alias)


def _register_operational_commands(sub: Any) -> None:
    p_auto = sub.add_parser("auto", help="run koru auto in a lane")
    _add_lane_identifiers(p_auto)
    p_auto.add_argument("rest", nargs=argparse.REMAINDER)

    p_daemon = sub.add_parser("daemon", help="run autopilot daemon in foreground for current lane")
    _add_lane_identifiers(p_daemon)
    p_daemon.add_argument(
        "--allow-integrated-shell",
        action="store_true",
        help="allow running daemon from IDE integrated terminal",
    )

    p_supervisor = sub.add_parser("supervisor", help="background lane registry and daemon supervisor")
    p_supervisor.add_argument("supervisor_args", nargs=argparse.REMAINDER)


def _register_interaction_commands(sub: Any) -> None:
    p_text = sub.add_parser("text", help="natural language command")
    p_text.add_argument("prompt")
    p_text.add_argument("--llm", action="store_true", help="use litellm planner first")
    _add_shell_argument(p_text)
    p_text.add_argument("--single-action", action="store_true", help="execute only one mapped action")

    p_chat = sub.add_parser("chat", help="interactive chat-first mode")
    p_chat.add_argument("--llm", action="store_true", help="use litellm planner first")
    _add_shell_argument(p_chat)
    p_chat.add_argument("--single-action", action="store_true", help="execute only one mapped action")
    p_chat.add_argument(
        "--require-plugin",
        action="store_true",
        default=True,
        help="require connected IDE plugin transport (disable keyboard fallback)",
    )
    p_chat.add_argument(
        "--allow-keyboard-fallback",
        dest="require_plugin",
        action="store_false",
        help="allow OS keyboard injection fallback when plugin transport is unavailable",
    )


def _register_repair_command(sub: Any) -> None:
    p_repair = sub.add_parser("repair", help="bridge autorepair with event-sourced history")
    repair_sub = p_repair.add_subparsers(dest="repair_command", required=True)

    p_history = repair_sub.add_parser("history", help="show repair case history for LLM/operators")
    p_history.add_argument("--limit", type=int, default=20)
    p_history.add_argument("--code", default=None, help="filter sessions that included this problem code")
    p_history.add_argument(
        "--format",
        choices=("llm", "json"),
        default="llm",
        help="llm: markdown brief for agents; json: structured case rows",
    )
    _add_lane_identifiers(p_history)

    p_run = repair_sub.add_parser("run", help="detect problems and run registry repair pipeline")
    p_run.add_argument("--fix", action="store_true", help="alias; repair always runs when problems exist")
    _add_lane_identifiers(p_run)


def _register_sync_command(sub: Any) -> None:
    p_sync = sub.add_parser(
        "sync",
        help="auto-update koru ecosystem (python packages + VSIX plugins + repair)",
    )
    _add_lane_identifiers(p_sync)
    p_sync.add_argument(
        "--all-ides",
        action="store_true",
        help=(
            "sync plugins/repair for running VS Code-family IDEs "
            "(skips Antigravity unless selected with --ide antigravity)"
        ),
    )
    p_sync.add_argument("--skip-python", action="store_true", help="skip pip install -U")
    p_sync.add_argument("--skip-plugins", action="store_true", help="skip VSIX install-plugin")
    p_sync.add_argument("--skip-repair", action="store_true", help="skip manage --fix and self repair")
    p_sync.add_argument("--format", choices=("human", "json"), default="human")


def _register_doctor_command(sub: Any) -> None:
    p_doctor = sub.add_parser("doctor", help="orchestrated diagnostics (status/fix/probe) for current lane")
    _add_lane_identifiers(p_doctor)
    p_doctor.add_argument("--fix", action="store_true", help="run `koru ide doctor --fix --gc-sockets`")
    p_doctor.add_argument("--probe", action="store_true", help="run plugin-required drive probe")
    p_doctor.add_argument("--probe-prompt", default="test", help="prompt used by --probe")
    p_doctor.add_argument(
        "--allow-integrated-shell",
        action="store_true",
        help="allow running diagnostics from IDE integrated terminal",
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="coru")
    sub = p.add_subparsers(dest="command", required=False)

    p_ensure = sub.add_parser("ensure", help="check/install koruenv + koru + coru")
    p_ensure.add_argument("--install", action="store_true")

    sub.add_parser("setup", help="prepare preferred repo-local environment")

    _register_sync_command(sub)

    _register_lane_commands(sub)
    _register_operational_commands(sub)
    _register_interaction_commands(sub)
    _register_calibration_command(sub)
    _register_doctor_command(sub)
    _register_repair_command(sub)

    return p
