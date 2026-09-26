

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from coru.cli import AutoReadiness
def _resolve_readiness_lane(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> tuple[str, str]:
    if not payload:
        return ide, instance
    resolved_ide = str(payload.get("ide") or ide)
    resolved_instance = str(payload.get("instance") or instance)
    if resolved_ide != ide or resolved_instance != instance:
        print(
            f"[coru] readiness: lane resolved to ide={resolved_ide} instance={resolved_instance}",
            file=sys.stderr,
        )
    return resolved_ide, resolved_instance


def _maybe_auto_repair_lane(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> None:
    from coru.cli import _env_enabled, _lane_status_payload, _print_ide_control_context, _run_lane_repair
    if not _env_enabled("CORU_AUTO_REPAIR", default=False):
        return
    repair_plan = _run_lane_repair(ide, instance, payload=payload, trigger="coru.doctor")
    if repair_plan.resolved or not _env_enabled("CORU_AUTO_READINESS_GATE", default=True):
        return
    _print_ide_control_context(
        ide,
        instance,
        status=_lane_status_payload(ide, instance, payload=payload),
        reason="repair",
        guidance=True,
    )


def _readiness_plugin_blocker(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> AutoReadiness | None:
    from coru.cli import AutoReadiness, _fetch_manage_report, _lane_status_payload, _print_ide_control_context
    plugin_blocker = _manage_report_plugin_blocker(_fetch_manage_report(ide, instance))
    if plugin_blocker is None:
        return None
    code, message, fix = plugin_blocker
    print(f"[coru] readiness: [FAIL] {code}: {message}", file=sys.stderr)
    if fix:
        print(f"[coru] readiness: fix → {fix}", file=sys.stderr)
    _print_ide_control_context(
        ide,
        instance,
        status=_lane_status_payload(ide, instance, payload=payload),
        reason="plugin-version",
        guidance=True,
    )
    return AutoReadiness(1, ide, instance, reason="plugin")


def _readiness_consistency_step(
    ide: str, instance: str, payload: dict[str, Any] | None
) -> AutoReadiness | None:
    from coru.cli import AutoReadiness, _diagnose_runtime_consistency
    rc = _diagnose_runtime_consistency(ide, instance, payload)
    if rc != 0:
        return AutoReadiness(rc, ide, instance, reason="runtime")
    return None


def _readiness_daemon_step(ide: str, instance: str) -> AutoReadiness | None:
    from coru.cli import (
        AutoReadiness,
        _ensure_daemon_running,
        _env_enabled,
        _gc_stale_lane_socket,
        _lane_status_raw,
        _print_ide_control_context,
    )
    if _env_enabled("CORU_AUTO_SOCKET_GC", default=True) and _lane_status_raw(ide, instance) != 0:
        _gc_stale_lane_socket(ide, instance)
    daemon_rc = _ensure_daemon_running(ide, instance)
    if daemon_rc != 0:
        _print_ide_control_context(ide, instance, reason="daemon", guidance=True)
        return AutoReadiness(daemon_rc, ide, instance, reason="daemon")
    return None


def _readiness_blocker_step(
    ide: str, instance: str, payload: dict[str, Any] | None
) -> AutoReadiness | None:
    from coru.cli import AutoReadiness, _check_lane_status_and_ownership
    _maybe_auto_repair_lane(ide, instance, payload)
    blocked = _readiness_plugin_blocker(ide, instance, payload)
    if blocked is not None:
        return blocked
    rc, reason = _check_lane_status_and_ownership(ide, instance, payload)
    return AutoReadiness(rc, ide, instance, reason=reason)


def _auto_readiness_gate(ide: str, instance: str) -> AutoReadiness:
    from coru.cli import AutoReadiness, _env_enabled, _koru_autopilot_env_payload, _print_terminal_context
    if not _env_enabled("CORU_AUTO_READINESS_GATE", default=True):
        return AutoReadiness(0, ide, instance)

    print(f"[coru] readiness: ide={ide} instance={instance}", file=sys.stderr)
    _print_terminal_context()
    payload = _koru_autopilot_env_payload(ide, instance)
    ide, instance = _resolve_readiness_lane(ide, instance, payload)

    result = _readiness_consistency_step(ide, instance, payload)
    if result is not None:
        return result

    result = _readiness_daemon_step(ide, instance)
    if result is not None:
        return result

    return _readiness_blocker_step(ide, instance, payload)


def _resolve_daemon_alignment(
    readiness: Any,
    daemon: Any,
    status: dict[str, Any],
    root: Path,
    socket_path: Path,
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> tuple[Any, dict[str, Any]]:
    from coru.cli import _coru_projects_equivalent
    if not daemon.ok and _readiness_issue_codes(daemon) == {"daemon_project_mismatch"}:
        meta = status.get("daemon_metadata") if isinstance(status.get("daemon_metadata"), dict) else {}
        meta_project = str(meta.get("project") or "").strip()
        if meta_project and _coru_projects_equivalent(meta_project, root):
            from koru.autonomous_readiness import ReadinessResult

            daemon = ReadinessResult(ok=True, issues=())
        else:
            status = _restart_stale_lane_daemon(ide, instance, payload=payload)
            if status is not None:
                daemon = readiness.check_daemon_client_alignment(status, project=root, socket_path=socket_path)
    if not daemon.ok and _readiness_issue_codes(daemon) == {"daemon_version_mismatch"}:
        status = _restart_stale_lane_daemon(ide, instance, payload=payload)
        if status is not None:
            daemon = readiness.check_daemon_client_alignment(status, project=root, socket_path=socket_path)
    return daemon, status


def _build_ownership_checks(
    readiness: Any,
    daemon: Any,
    root: Path,
    socket_path: Path,
    status: dict[str, Any],
    ide: str,
    instance: str,
) -> list[Any]:
    from coru.cli import _status_has_target_plugin, _terminal_host_kind, _terminal_shell_context
    terminal_ide, _terminal_source, terminal_integrated = _terminal_shell_context()
    terminal_kind = _terminal_host_kind()
    terminal_integrated_for_lane = terminal_integrated
    if terminal_integrated and terminal_ide != ide and _status_has_target_plugin(status, ide=ide, project=root):
        terminal_integrated_for_lane = False
    return [
        daemon,
        readiness.check_workspace_socket_ownership(root, socket_path, status, autopilot_ide=ide),
        readiness.check_lane_terminal_socket_alignment(
            autopilot_ide=ide,
            lane_instance=instance,
            socket_path=socket_path,
            terminal_ide=terminal_ide,
            terminal_integrated=terminal_integrated_for_lane,
            terminal_kind=terminal_kind,
        ),
    ]


def _apply_ownership_check(
    readiness: Any,
    result: Any,
    *,
    root: Path,
    socket_path: Path,
) -> tuple[bool, str | None]:
    for line in readiness.format_readiness_lines(result, prefix="[coru]"):
        print(line, file=sys.stderr)
    if result.ok:
        return False, None
    primary_fix = result.primary_fix
    if hasattr(readiness, "apply_socket_ownership_repairs"):
        repair_result = readiness.apply_socket_ownership_repairs(root, socket_path, result)
        for action in repair_result.repair_actions:
            print(f"[coru] readiness repair: {action}", file=sys.stderr)
    return True, primary_fix


def _prepare_ownership_context(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> tuple[Any, Path, Path, dict[str, Any]] | None:
    from coru.cli import (
        _active_project_root,
        _import_koru_readiness_module,
        _lane_status_payload,
        _print_ide_control_context,
    )
    readiness = _import_koru_readiness_module()
    root = _active_project_root()
    socket_raw = str((payload or {}).get("socket") or "").strip()
    if readiness is None or root is None or not socket_raw:
        return None
    status = _lane_status_payload(ide, instance, payload=payload)
    if status is None:
        _print_ide_control_context(ide, instance, reason="ownership", guidance=True)
        return None
    _print_ide_control_context(ide, instance, status=status, reason="ownership", guidance=False)
    return readiness, root, Path(socket_raw), status


def _run_ownership_checks_loop(
    readiness: Any,
    checks: list[Any],
    root: Path,
    socket_path: Path,
) -> tuple[bool, str | None]:
    failed = False
    primary_fix: str | None = None
    for result in checks:
        check_failed, fix = _apply_ownership_check(
            readiness,
            result,
            root=root,
            socket_path=socket_path,
        )
        if check_failed:
            failed = True
            primary_fix = primary_fix or fix
    return failed, primary_fix


def _auto_ownership_gate(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None,
) -> int:
    from coru.cli import _print_ide_control_context
    ctx = _prepare_ownership_context(ide, instance, payload)
    if ctx is None:
        return 0
    readiness, root, socket_path, status = ctx

    daemon = readiness.check_daemon_client_alignment(status, project=root, socket_path=socket_path)
    daemon, status = _resolve_daemon_alignment(readiness, daemon, status, root, socket_path, ide, instance, payload)
    checks = _build_ownership_checks(readiness, daemon, root, socket_path, status, ide, instance)

    failed, primary_fix = _run_ownership_checks_loop(readiness, checks, root, socket_path)
    if failed and primary_fix:
        print(f"[coru] readiness primary fix: {primary_fix}", file=sys.stderr)
        _print_ide_control_context(ide, instance, status=status, reason="readiness-failed", guidance=True)
    return 1 if failed else 0


def _readiness_issue_codes(result: Any) -> set[str]:
    issues = getattr(result, "issues", ()) or ()
    return {str(getattr(issue, "code", "") or "") for issue in issues}


def _restart_stale_lane_daemon(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    from coru.cli import _ensure_daemon_running, _env_enabled, _lane_status_payload, _run_koru_lane
    if not _env_enabled("CORU_AUTO_DAEMON_RESTART", default=True):
        return None
    print("[coru] readiness: daemon/client mismatch; restarting lane daemon...", file=sys.stderr)
    _run_koru_lane(ide, instance, ["autopilot", "shutdown"])
    if _ensure_daemon_running(ide, instance) != 0:
        return None
    return _lane_status_payload(ide, instance, payload=payload)


def _manage_report_plugin_blocker(
    report: Mapping[str, Any] | None,
) -> tuple[str, str, str | None] | None:
    from coru.cli import _BLOCKING_PLUGIN_MANAGE_CODES
    if not isinstance(report, Mapping):
        return None
    issues = report.get("issues")
    if not isinstance(issues, list):
        return None
    for issue in issues:
        if not isinstance(issue, Mapping):
            continue
        code = str(issue.get("code") or "").strip()
        severity = str(issue.get("severity") or "").strip().lower()
        if code not in _BLOCKING_PLUGIN_MANAGE_CODES or severity != "error":
            continue
        message = str(issue.get("message") or code)
        fix = issue.get("fix")
        return code, message, str(fix) if fix else None
    return None


def _auto_readiness_can_continue_without_plugin(readiness: AutoReadiness) -> bool:
    from coru.cli import _lane_status_payload, _status_has_keyboard_backend, _status_has_plugin_for_ide
    if readiness.reason not in {"plugin", "ownership"}:
        return False
    status = _lane_status_payload(readiness.ide, readiness.instance)
    if not isinstance(status, Mapping):
        return False
    if not status.get("daemon"):
        return False
    if _status_has_plugin_for_ide(status, readiness.ide):
        return False
    try:
        from koru.autonomy.env import plugin_required_for_ide
    except Exception:
        return False
    if plugin_required_for_ide(readiness.ide):
        return False
    try:
        from koru.integrations.vdisplay_client import vdisplay_fallback_enabled

        if vdisplay_fallback_enabled(ide=readiness.ide, plugin_connected=False):
            return True
    except Exception:
        pass
    return _status_has_keyboard_backend(status)


def _auto_readiness_can_continue_with_keyboard_fallback(readiness: AutoReadiness) -> bool:
    return _auto_readiness_can_continue_without_plugin(readiness)


def _run_auto_with_readiness(ide: str, instance: str, extra_args: Sequence[str]) -> int:
    from coru.cli import _auto_readiness_gate, _bind_lane_session, _lane_auto
    with _bind_lane_session(ide, instance):
        readiness = _auto_readiness_gate(ide, instance)
        if readiness.rc != 0:
            if _auto_readiness_can_continue_without_plugin(readiness):
                try:
                    from koru.integrations.vdisplay_client import vdisplay_fallback_enabled

                    fallback = (
                        "vdisplay semantic control"
                        if vdisplay_fallback_enabled(
                            ide=readiness.ide,
                            plugin_connected=False,
                        )
                        else "keyboard fallback"
                    )
                except Exception:
                    fallback = "keyboard fallback"
                print(
                    f"[coru] readiness: plugin is not connected, but {fallback} "
                    "is enabled; entering autonomous cycle",
                    file=sys.stderr,
                )
                return _lane_auto(readiness.ide, readiness.instance, extra_args)
            print(
                "[coru] readiness: autopilot bridge is not ready; "
                "not entering autonomous cycle",
                file=sys.stderr,
            )
            return readiness.rc
        return _lane_auto(readiness.ide, readiness.instance, extra_args)


def _lane_manage_fix(ide: str, instance: str) -> int:
    from coru.cli import _koru_exec_argv, _project_for_lane, _run_koru_lane
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    # Check first without --fix to avoid unnecessary repairs when the lane is
    # already healthy (e.g. plugin already installed and socket responsive).
    manage_args = ["autopilot", "manage", "--ide", ide]
    project = _project_for_lane(ide, instance)
    if project:
        manage_args.extend(["--project", project])
    rc = _run_koru_lane(ide, instance, manage_args)
    if rc == 0:
        return 0
    # Need repair.
    repair_args = ["autopilot", "manage", "--ide", ide, "--fix"]
    if project:
        repair_args.extend(["--project", project])
    rc = _run_koru_lane(ide, instance, repair_args)
    if rc != 0:
        rc = _run_koru_lane(
            ide,
            instance,
            ["ide", "doctor", "--ide", ide, "--fix", "--gc-sockets"],
        )
    return rc


def _lane_daemon_foreground(ide: str, instance: str) -> int:
    from coru.cli import _koru_exec_argv, _project_for_lane, _run_koru_lane
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    args = ["autopilot", "daemon", "--idempotent"]
    project = _project_for_lane(ide, instance)
    if project:
        args.extend(["--project", project])
    return _run_koru_lane(ide, instance, args)
