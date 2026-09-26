from __future__ import annotations

import argparse
import functools  # noqa: F401
import json  # noqa: F401
import os
import re  # noqa: F401
import shutil  # noqa: F401
import subprocess
import sys
import time  # noqa: F401
from collections.abc import Mapping, Sequence  # noqa: F401
from contextlib import contextmanager  # noqa: F401
from dataclasses import dataclass, field
from datetime import UTC, datetime  # noqa: F401
from importlib import metadata  # noqa: F401
from pathlib import Path
from typing import Any  # noqa: F401

# coru.cli is a facade over the cli_* modules: every import below is part of the
# historical public/test surface (tests do `from coru.cli import X` and monkeypatch
# coru.cli.<module>.<attr>), so unused re-exports stay bound under an explicit noqa.
from coru import ide_detection, repair_registry  # noqa: F401
from coru.repair import RecordDiagnosisCommand, RepairHistoryQuery, RepairService  # noqa: F401
from coru.cli_checks import (
    _coru_normalize_project,
    _coru_projects_equivalent,  # noqa: F401
    _coru_readiness_strict,  # noqa: F401
    _status_failure_ok_to_continue,  # noqa: F401
    _status_has_keyboard_backend,  # noqa: F401
    _status_has_plugin_for_ide,  # noqa: F401
    _status_has_target_plugin,  # noqa: F401
    _trace,  # noqa: F401
    _trace_enabled,  # noqa: F401
)
from coru.cli_doctor import (
    _check_lane_status_and_ownership,  # noqa: F401
    _collect_lane_repair_problems,  # noqa: F401
    _drive_result_from_payload,  # noqa: F401
    _env_enabled,  # noqa: F401
    _fetch_manage_report,  # noqa: F401
    _gc_stale_lane_socket,  # noqa: F401
    _lane_alignment_problems,  # noqa: F401
    _lane_auto,  # noqa: F401
    _lane_doctor,
    _lane_status,
    _lane_status_env,  # noqa: F401
    _lane_status_payload,  # noqa: F401
    _lane_status_raw,  # noqa: F401
    _manage_repair_context,  # noqa: F401
    _plugin_workspace_summary,  # noqa: F401
    _print_ide_control_context,  # noqa: F401
    _problem_from_readiness_issue,  # noqa: F401
    _refactor_intent,  # noqa: F401
    _repair_connect_plugin,  # noqa: F401
    _repair_reload_ide,  # noqa: F401
    _repair_strict_handshake_cycle,  # noqa: F401
    _run_lane_repair,
    _run_lane_status_json,  # noqa: F401
    _running_ide_summary,  # noqa: F401
    _runtime_readiness_problems,  # noqa: F401
    _subprocess_blocked_in_tests,  # noqa: F401
    _target_plugin_rows,  # noqa: F401
)
from coru.cli_diagnose import (
    _attempt_plugin_self_heal,  # noqa: F401
    _chat_llm_enabled,  # noqa: F401
    _diagnose_lane,
    _diagnose_lane_status,  # noqa: F401
    _diagnose_readiness_alignment,  # noqa: F401
    _diagnose_runtime_consistency,  # noqa: F401
    _ensure_daemon_running,  # noqa: F401
    _fetch_drive_payload,  # noqa: F401
    _import_koru_readiness_module,  # noqa: F401
    _koru_exec_argv,
    _lane_chat_prompt,  # noqa: F401
    _llm_rewrite_chat_prompt,  # noqa: F401
    _print_troubleshooting_log_locations,
    _resolve_diagnose_lane,  # noqa: F401
    _start_autopilot_daemon_for_lane,  # noqa: F401
    _warn_koru_exec_outside_repo,  # noqa: F401
    _warn_lane_project_mismatch,  # noqa: F401
    _warn_python_env_mismatch,  # noqa: F401
)
from coru.cli_daemon import (
    _KORU_SUBPROCESS_TIMEOUT_S,  # noqa: F401
    _alive_daemon_ide,  # noqa: F401
    _auto_default_instance,  # noqa: F401
    _bind_lane_session,
    _connected_daemon_from_meta,  # noqa: F401
    _connected_daemon_instance,  # noqa: F401
    _env_default_ide,  # noqa: F401
    _environment_default_instance,  # noqa: F401
    _infer_default_ide,  # noqa: F401
    _infer_default_instance,  # noqa: F401
    _integrated_terminal_default_ide,  # noqa: F401
    _is_lane_plugin_connected,  # noqa: F401
    _koru_autopilot_env_payload,
    _koruenv_run_fallback,  # noqa: F401
    _lane_env,
    _maybe_warn_lane_override,  # noqa: F401
    _prefer_terminal_over_lane,  # noqa: F401
    _project_ide_settings_instance,  # noqa: F401
    _project_settings_default_ide,  # noqa: F401
    _run_koru_lane,
    _run_with_lane_environment,  # noqa: F401
    _run_with_resolved_lane_env,  # noqa: F401
    _supervisor_default_ide,  # noqa: F401
    _supervisor_default_instance,  # noqa: F401
    _supervisor_lane_defaults,  # noqa: F401
    _supervisor_lane_project,
    _warn_integrated_terminal_daemon_mismatch,  # noqa: F401
    _workspace_default_instance,  # noqa: F401
)
from coru.cli_parser import (
    _add_lane_identifiers,  # noqa: F401
    _add_shell_argument,  # noqa: F401
    _build_parser,
    _register_doctor_command,  # noqa: F401
    _register_interaction_commands,  # noqa: F401
    _register_lane_commands,  # noqa: F401
    _register_operational_commands,  # noqa: F401
    _register_repair_command,  # noqa: F401
    _register_sync_command,  # noqa: F401
)
from coru.cli_readiness import (
    _apply_ownership_check,  # noqa: F401
    _auto_ownership_gate,  # noqa: F401
    _auto_readiness_can_continue_with_keyboard_fallback,  # noqa: F401
    _auto_readiness_can_continue_without_plugin,  # noqa: F401
    _auto_readiness_gate,  # noqa: F401
    _build_ownership_checks,  # noqa: F401
    _lane_daemon_foreground,
    _lane_manage_fix,  # noqa: F401
    _manage_report_plugin_blocker,  # noqa: F401
    _maybe_auto_repair_lane,  # noqa: F401
    _prepare_ownership_context,  # noqa: F401
    _readiness_blocker_step,  # noqa: F401
    _readiness_consistency_step,  # noqa: F401
    _readiness_daemon_step,  # noqa: F401
    _readiness_issue_codes,  # noqa: F401
    _readiness_plugin_blocker,  # noqa: F401
    _resolve_daemon_alignment,  # noqa: F401
    _resolve_readiness_lane,  # noqa: F401
    _restart_stale_lane_daemon,  # noqa: F401
    _run_auto_with_readiness,
    _run_ownership_checks_loop,  # noqa: F401
)
from coru.cli_plan import (
    _build_plan_chain,
    _chat_drive_with_retry,  # noqa: F401
    _chat_ensure_daemon,  # noqa: F401
    _chat_handle_command,  # noqa: F401
    _chat_handle_drive,  # noqa: F401
    _chat_loop,
    _chat_print_header,  # noqa: F401
    _default_lane,
    _dispatch_plan_action,  # noqa: F401
    _emit_plan_step_log,  # noqa: F401
    _execute_plan,  # noqa: F401
    _heuristic_plan,  # noqa: F401
    _import_heuristic_plan_fn,  # noqa: F401
    _intent_to_plan,  # noqa: F401
    _llm_plan,  # noqa: F401
    _plan_failure_return,  # noqa: F401
    _plan_step_identity,  # noqa: F401
    _preflight_failure_ok_to_continue,  # noqa: F401
    _resolve_defaults,
    _run_single_plan_with_logging,
)
from coru.cli_lane import (
    LANE_SESSION_ENV_KEYS as _LANE_SESSION_ENV_KEYS_FROM_LANE,
    VALID_AUTOPILOT_IDES as _VALID_AUTOPILOT_IDES,
    WORKSPACE_SETTINGS_BY_IDE as _WORKSPACE_SETTINGS_BY_IDE,  # noqa: F401
    _apply_strict_plugin_policy_defaults,  # noqa: F401
    _ide_from_instance,  # noqa: F401
    _instance_from_socket_path,  # noqa: F401
    _instance_matches_ide,  # noqa: F401
    _lane_subprocess_env,  # noqa: F401
    _load_project_ide_settings,  # noqa: F401
    _normalize_lane_pair,  # noqa: F401
    _project_ide_settings_lane,  # noqa: F401
    _project_ide_settings_path,  # noqa: F401
    _remember_project_ide_settings,
    _workspace_lane_hint,  # noqa: F401
    _workspace_settings_path_for_ide,  # noqa: F401
    _workspace_socket_path_for_ide,  # noqa: F401
)
from coru.cli_reexec import (
    _already_running_in_project_venv,  # noqa: F401
    _cwd_repo_root,  # noqa: F401
    _installed_module_source_dir,  # noqa: F401
    _local_module_source_dir,  # noqa: F401
    _maybe_reexec_into_project_python,
    _module_runtime_source_dir,  # noqa: F401
    _project_repo_root,  # noqa: F401
    _project_venv_candidates,  # noqa: F401
    _project_venv_python,
    _reexec_already_done,  # noqa: F401
    _reexec_env_and_cmd,  # noqa: F401
    _repo_root,
    _venv_has_installed_module,  # noqa: F401
)
from coru.cli_terminal import _print_terminal_context  # noqa: F401
from coru.cli_startup import (
    _agent_lane_from_auto_args,  # noqa: F401
    _alive_daemon_instance,  # noqa: F401
    _autonomous_startup_chain,  # noqa: F401
    _binary_path,  # noqa: F401
    _chain_project_from_plans,
    _choose_option,  # noqa: F401
    _cmd_exists,  # noqa: F401
    _current_log_format,  # noqa: F401
    _distribution_version,  # noqa: F401
    _emit_log,  # noqa: F401
    _enforce_runtime_readiness,  # noqa: F401
    _ensure_commands,
    _extract_global_flags,
    _instance_for_ide_choice,
    _interactive_default_auto_args,
    _interactive_select_agent_lane,  # noqa: F401
    _interactive_select_project_arg,  # noqa: F401
    _koru_subprocess_timeout,  # noqa: F401
    _local_install_target,  # noqa: F401
    _normalize_log_format,  # noqa: F401
    _print_autonomous_banner,  # noqa: F401
    _print_runtime_versions,
    _project_from_argv,  # noqa: F401
    _python_module_exists,  # noqa: F401
    _run,  # noqa: F401
    _run_default_autonomous,
    _running_ide_choices,  # noqa: F401
    _runtime_metadata_roots,  # noqa: F401
    _setup_environment,
    _startup_mode,
    _supervisor_project_choices,  # noqa: F401
    _tool_argv,  # noqa: F401
    _tool_available,  # noqa: F401
)

_LANE_ENV_KEYS = ("KORU_AUTOPILOT_IDE", "KORU_AUTOPILOT_INSTANCE", "KORU_AUTOPILOT_SOCKET")
_STRICT_PLUGIN_ENV_KEYS = (
    "KORU_STRICT_PLUGIN_VERSION",
    "KORU_STRICT_PLUGIN_ACK",
    "KORU_PLUGIN_VERSION_POLICY",
)
_LANE_SESSION_ENV_KEYS = _LANE_SESSION_ENV_KEYS_FROM_LANE
_ORIGINAL_SUBPROCESS_RUN = subprocess.run

from coru import control as _coru_control  # noqa: E402

_ORIGINAL_APPLY_NL = _coru_control.apply_nl
_LANE_ENV_PAYLOAD_TIMEOUT_S = float(os.environ.get("CORU_LANE_ENV_PAYLOAD_TIMEOUT_S", "5"))


@dataclass(frozen=True)
class Plan:
    action: str
    ide: str | None = None
    instance: str | None = None
    text: str = ""
    install: bool = False
    auto_args: tuple[str, ...] = ()


@dataclass
class SessionContext:
    ide: str | None = None
    instance: str | None = None
    project: str | None = None
    lane_override_warned: bool = False


@dataclass(frozen=True)
class AutoReadiness:
    rc: int
    ide: str
    instance: str
    reason: str = field(default="", compare=False)


_CHAIN_CONTEXT: SessionContext | None = None


def _active_project_root() -> Path | None:
    ctx = _CHAIN_CONTEXT
    if ctx is not None and ctx.project:
        return _coru_normalize_project(ctx.project)
    return _repo_root()


_VALID_LOG_FORMATS = frozenset({"human", "jsonl"})
_VALID_STARTUP_MODES = frozenset({"auto", "chat"})
_FALSE_ENV_VALUES = frozenset({"0", "false", "no", "off"})
_BLOCKING_PLUGIN_MANAGE_CODES = frozenset(
    {
        "plugin_build_missing",
        "plugin_build_mismatch",
        "plugin_installed_version_mismatch",
        "plugin_live_host_stale",
        "plugin_version_missing",
        "plugin_version_mismatch",
    }
)


_PROJECT_IDE_SETTINGS_NAME = "settings.json"


def _ide_from_vscode_pid() -> str | None:
    """Backward-compatible shim; moved to ``coru.ide_detection``."""
    return ide_detection._ide_from_vscode_pid()


def _vscode_family_env_hint() -> str | None:
    """Backward-compatible shim; moved to ``coru.ide_detection``."""
    return ide_detection._vscode_family_env_hint()


def _windsurf_terminal_marker() -> bool:
    """Backward-compatible shim; moved to ``coru.ide_detection``."""
    return ide_detection._windsurf_terminal_marker()


def _terminal_ide_hint() -> str | None:
    """Best-effort IDE owning this shell."""
    ide, _source, _integrated = _terminal_shell_context()
    return ide


def _terminal_shell_context() -> tuple[str | None, str, bool]:
    """Return ``(ide, source, integrated)`` for the current shell context."""
    fallback = _terminal_shell_context_fallback()
    if fallback[2]:
        return fallback
    try:
        from koruide.ide import detect_terminal_host_context
        ctx = detect_terminal_host_context()
        return ctx.ide, ctx.source, ctx.integrated
    except Exception:
        return fallback


def _terminal_host_kind() -> str:
    return ide_detection.terminal_host_kind()


def _terminal_shell_context_fallback() -> tuple[str | None, str, bool]:
    """Provider-first shell context detection (brand name before generic vscode)."""
    return ide_detection._terminal_shell_context_fallback(
        ide_from_vscode_pid=_ide_from_vscode_pid,
        vscode_family_env_hint=_vscode_family_env_hint,
        windsurf_terminal_marker=_windsurf_terminal_marker,
    )


def _project_for_lane(ide: str, instance: str) -> str | None:
    ctx = _CHAIN_CONTEXT
    if ctx is not None and ctx.project:
        return ctx.project
    supervisor = _supervisor_lane_project(instance)
    if supervisor:
        return supervisor
    root = _repo_root()
    if root is not None:
        return str(root)
    return None


from coru.cli_calibration import (  # noqa: E402
    _CALIBRATION_DRIVE_TIMEOUT_S,  # noqa: F401
    _calibration_desktop_focus_titles,  # noqa: F401
    _format_calibration_bridge_report,  # noqa: F401
    _format_calibration_desktop_report,  # noqa: F401
    _format_calibration_probe_report,  # noqa: F401
    _lane_calibration,
    _lane_drive_capture,  # noqa: F401
    _materialize_calibration_desktop_oql,  # noqa: F401
    _parse_drive_json_from_stdout,  # noqa: F401
    _register_calibration_command,  # noqa: F401
    _resolve_calibration_lane,
    _run_calibration_bridge_preflight,  # noqa: F401
    _run_calibration_desktop_preflight,  # noqa: F401
    _write_calibration_bridge_testql,  # noqa: F401
    _write_calibration_desktop_oql,  # noqa: F401
)


_REFACTOR_MARKERS = (
    "refactor",
    "refaktoryz",
    "refakotryz",  # common typo: missing 't' (refakotryzuj vs refaktoryzuj)
)


def _execute_plans(
    plans: Sequence[Plan],
    *,
    shell: str = "bash",
    context: SessionContext | None = None,
    announce: bool = False,
) -> int:
    global _CHAIN_CONTEXT
    ctx = context or SessionContext()
    chain_project = _chain_project_from_plans(plans)
    if chain_project and not ctx.project:
        ctx.project = chain_project
    plans_list = list(plans)
    if not plans_list:
        return 0
    bootstrap = _resolve_defaults(plans_list[0], context=ctx)
    rc = 0
    previous_chain_context = _CHAIN_CONTEXT
    _CHAIN_CONTEXT = ctx
    try:
        with _bind_lane_session(bootstrap.ide, bootstrap.instance):
            for index, plan in enumerate(plans_list):
                result = _run_single_plan_with_logging(
                    plan, index=index, plans_list=plans_list, ctx=ctx, shell=shell, announce=announce
                )
                if result is not None and result != 0:
                    return result
                if result is None:
                    continue
                rc = result
        return rc
    finally:
        _CHAIN_CONTEXT = previous_chain_context


def _cmd_repair_history(args: argparse.Namespace) -> int:
    ide, instance = _default_lane(args.ide, args.instance)
    root = _repo_root()
    if root is None:
        print("[coru] repair history: no repo root; run from a git project", file=sys.stderr)
        return 1
    query = RepairHistoryQuery.for_project(root)
    if args.format == "json":
        print(query.format_json(limit=args.limit, code=args.code))
    else:
        print(query.format_llm(limit=args.limit, code=args.code))
    print(f"[coru] repair: lane filter ide={ide} instance={instance}", file=sys.stderr)
    print(f"[coru] repair: event log → {query.store_path}", file=sys.stderr)
    return 0


def _cmd_repair_run(args: argparse.Namespace) -> int:
    ide, instance = _default_lane(args.ide, args.instance)
    payload = _koru_autopilot_env_payload(ide, instance)
    plan = _run_lane_repair(ide, instance, payload=payload, trigger="coru.repair.run")
    return 0 if plan.resolved else 1


def _cmd_sync(args: argparse.Namespace) -> int:
    from coru.ecosystem import format_sync_report, format_sync_report_json, sync_ecosystem

    root = _repo_root()
    if root is None:
        print("error: coru sync requires a koru git checkout", file=sys.stderr)
        return 2

    ide, instance = _default_lane(args.ide, args.instance)
    resolved = _resolve_defaults(Plan(action="sync", ide=ide, instance=instance))

    def _koru_runner(target_ide: str, koru_args: Sequence[str]) -> int:
        lane_instance = _instance_for_ide_choice(target_ide)
        return _run_koru_lane(target_ide, lane_instance, list(koru_args))

    target_ide = None if args.all_ides else resolved.ide
    report = sync_ecosystem(
        root,
        ide=target_ide,
        python=not args.skip_python,
        plugins=not args.skip_plugins,
        repair=not args.skip_repair,
        all_running_ides=args.all_ides,
        python_executable=_project_venv_python() or sys.executable,
        koru_runner=_koru_runner if (not args.skip_plugins or not args.skip_repair) else None,
    )

    if args.format == "json":
        print(format_sync_report_json(report))
    else:
        print(format_sync_report(report))
    return 0 if report.ok else 1


def _restore_log_format(previous_log_format: str | None) -> None:
    if previous_log_format is None:
        os.environ.pop("CORU_LOG_FORMAT", None)
    else:
        os.environ["CORU_LOG_FORMAT"] = previous_log_format


def _maybe_run_default_mode(raw_argv: Sequence[str], *, verbose: bool) -> int | None:
    if not raw_argv or (raw_argv[0] == "--" and len(raw_argv) == 1):
        if _startup_mode() == "chat":
            return _chat_loop(
                use_llm=False,
                shell="bash",
                single_action=False,
                verbose=verbose,
                require_plugin=True,
            )
        auto_args: list[str] = []
        if raw_argv and raw_argv[0] == "--":
            auto_args = list(raw_argv[1:])
        elif not raw_argv:
            auto_args = _interactive_default_auto_args()
        return _run_default_autonomous(auto_args, shell="bash", verbose=verbose)
    if raw_argv[0] == "--":
        return _run_default_autonomous(raw_argv[1:], shell="bash", verbose=verbose)
    return None


def _maybe_rewrite_ide_auto_shorthand(
    raw_argv: Sequence[str],
    known_commands: set[str],
) -> list[str] | None:
    """``coru cursor auto`` → ``coru auto cursor`` (documented lane hint syntax)."""
    if len(raw_argv) < 2:
        return None
    if raw_argv[0] in known_commands or raw_argv[0].startswith("-"):
        return None
    ide = raw_argv[0].strip().lower()
    if ide not in _VALID_AUTOPILOT_IDES or raw_argv[1].strip().lower() != "auto":
        return None
    return ["auto", ide, *raw_argv[2:]]


def _is_text_shorthand(raw_argv: Sequence[str], known_commands: set[str]) -> bool:
    if not raw_argv:
        return False
    token = raw_argv[0]
    return token not in known_commands and not token.startswith("-")


def _rewrite_text_shorthand_argv(
    raw_argv: Sequence[str],
    *,
    verbose: bool,
    log_format: str,
    require_plugin: bool,
) -> list[str]:
    nested_argv = ["text", " ".join(raw_argv)]
    if verbose:
        nested_argv = ["--verbose", *nested_argv]
    if log_format != "human":
        nested_argv = [f"--log-format={log_format}", *nested_argv]
    if require_plugin:
        nested_argv = ["--require-plugin", *nested_argv]
    return nested_argv


def _doctor_or_daemon_requires_system_shell(
    *,
    command: str,
    allow_integrated_shell: bool,
) -> bool:
    term_ide, term_source, integrated = _terminal_shell_context()
    if not integrated or allow_integrated_shell:
        return False
    print(
        f"coru {command}: run this from system shell (outside IDE integrated terminal); "
        f"detected integrated ide={term_ide or '-'} source={term_source}",
        file=sys.stderr,
    )
    print("hint: rerun with --allow-integrated-shell only when necessary", file=sys.stderr)
    return True


def _run_text_plan_chain(args: argparse.Namespace, *, verbose: bool) -> int:
    plans = _build_plan_chain(
        args.prompt,
        use_llm=args.llm,
        single_action=args.single_action,
    )
    return _execute_plans(plans, shell=args.shell, announce=verbose)


def _dispatch_lane_command(args: argparse.Namespace) -> int | None:
    from coru.cli_dispatch import dispatch_lane_command

    return dispatch_lane_command(
        args,
        default_lane=_default_lane,
        lane_env=_lane_env,
        lane_status=_lane_status,
        diagnose_lane=_diagnose_lane,
    )


def _dispatch_auto_command(args: argparse.Namespace) -> int | None:
    from coru.cli_dispatch import dispatch_auto_command

    return dispatch_auto_command(
        args,
        default_lane=_default_lane,
        remember_settings=_remember_project_ide_settings,
        run_auto=_run_auto_with_readiness,
    )


def _dispatch_text_command(args: argparse.Namespace, *, verbose: bool) -> int | None:
    from coru.cli_dispatch import dispatch_text_command

    return dispatch_text_command(
        args,
        verbose=verbose,
        original_apply_nl=_ORIGINAL_APPLY_NL,
        run_text_plan_chain=_run_text_plan_chain,
    )


def _dispatch_chat_command(
    args: argparse.Namespace,
    *,
    verbose: bool,
    require_plugin: bool,
) -> int | None:
    from coru.cli_dispatch import dispatch_chat_command

    return dispatch_chat_command(
        args,
        verbose=verbose,
        require_plugin=require_plugin,
        chat_loop=_chat_loop,
    )


def _dispatch_supervisor_command(args: argparse.Namespace) -> int | None:
    from coru.cli_dispatch import dispatch_supervisor_command

    return dispatch_supervisor_command(args, koru_argv=_koru_exec_argv)


def _dispatch_calibration_command(args: argparse.Namespace) -> int | None:
    from coru.cli_dispatch import dispatch_calibration_command

    return dispatch_calibration_command(
        args,
        default_lane=_default_lane,
        resolve_calibration_lane=_resolve_calibration_lane,
        lane_calibration=_lane_calibration,
    )


def _dispatch_doctor_command(args: argparse.Namespace) -> int | None:
    from coru.cli_dispatch import dispatch_doctor_command

    return dispatch_doctor_command(
        args,
        default_lane=_default_lane,
        requires_system_shell=_doctor_or_daemon_requires_system_shell,
        lane_doctor=_lane_doctor,
    )


def _dispatch_repair_command(args: argparse.Namespace) -> int | None:
    from coru.cli_dispatch import dispatch_repair_command

    return dispatch_repair_command(
        args,
        cmd_history=_cmd_repair_history,
        cmd_run=_cmd_repair_run,
    )


def _dispatch_daemon_command(args: argparse.Namespace) -> int | None:
    from coru.cli_dispatch import dispatch_daemon_command

    return dispatch_daemon_command(
        args,
        default_lane=_default_lane,
        requires_system_shell=_doctor_or_daemon_requires_system_shell,
        resolve_defaults=_resolve_defaults,
        plan_cls=Plan,
        print_troubleshooting=_print_troubleshooting_log_locations,
        lane_daemon_foreground=_lane_daemon_foreground,
    )


def _dispatch_optional_command(
    args: argparse.Namespace,
    *,
    verbose: bool,
    require_plugin: bool,
) -> int | None:
    from coru.cli_dispatch import dispatch_optional_command

    return dispatch_optional_command(
        args,
        verbose=verbose,
        require_plugin=require_plugin,
        dispatchers=[
            lambda: _dispatch_lane_command(args),
            lambda: _dispatch_auto_command(args),
            lambda: _dispatch_text_command(args, verbose=verbose),
            lambda: _dispatch_chat_command(
                args, verbose=verbose, require_plugin=require_plugin
            ),
            lambda: _dispatch_supervisor_command(args),
            lambda: _dispatch_calibration_command(args),
            lambda: _dispatch_doctor_command(args),
            lambda: _dispatch_repair_command(args),
            lambda: _dispatch_daemon_command(args),
        ],
    )


def _dispatch_command(args: argparse.Namespace, *, verbose: bool, require_plugin: bool) -> int:
    from coru.cli_dispatch import dispatch_command

    return dispatch_command(
        args,
        verbose=verbose,
        require_plugin=require_plugin,
        ensure_commands=_ensure_commands,
        cmd_sync=_cmd_sync,
        setup_environment=_setup_environment,
        dispatch_optional=_dispatch_optional_command,
    )


_KNOWN_CORU_COMMANDS = frozenset(
    {
        "ensure",
        "setup",
        "sync",
        "lane",
        "lane-status",
        "status",
        "env",
        "auto",
        "text",
        "chat",
        "supervisor",
        "doctor",
        "calibration",
        "daemon",
        "repair",
    }
)


def _run_main_dispatch(
    raw_argv: list[str],
    *,
    verbose: bool,
    log_format: str,
    require_plugin: bool,
) -> int:
    default_mode_rc = _maybe_run_default_mode(raw_argv, verbose=verbose)
    if default_mode_rc is not None:
        return default_mode_rc
    ide_auto_argv = _maybe_rewrite_ide_auto_shorthand(raw_argv, _KNOWN_CORU_COMMANDS)
    if ide_auto_argv is not None:
        raw_argv = ide_auto_argv
    if _is_text_shorthand(raw_argv, _KNOWN_CORU_COMMANDS):
        nested_argv = _rewrite_text_shorthand_argv(
            raw_argv,
            verbose=verbose,
            log_format=log_format,
            require_plugin=require_plugin,
        )
        return main(nested_argv)
    args = _build_parser().parse_args(raw_argv)
    return _dispatch_command(args, verbose=verbose, require_plugin=require_plugin)


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else list(sys.argv[1:])
    if _maybe_reexec_into_project_python(raw_argv):
        return 0
    raw_argv, verbose, show_version, log_format, require_plugin = _extract_global_flags(raw_argv)
    previous_log_format = os.environ.get("CORU_LOG_FORMAT")
    os.environ["CORU_LOG_FORMAT"] = log_format
    if show_version:
        _print_runtime_versions()
        _restore_log_format(previous_log_format)
        return 0
    try:
        return _run_main_dispatch(
            raw_argv,
            verbose=verbose,
            log_format=log_format,
            require_plugin=require_plugin,
        )
    finally:
        _restore_log_format(previous_log_format)


if __name__ == "__main__":
    raise SystemExit(main())
