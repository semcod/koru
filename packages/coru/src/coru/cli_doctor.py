"""Lane status payloads, repair orchestration, doctor and auto-lane helpers extracted from ``coru.cli``."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from coru import repair_registry
from coru.repair import RecordDiagnosisCommand, RepairService

def _lane_status_raw(ide: str, instance: str) -> int:
    from coru.cli import _koru_exec_argv, _run_koru_lane
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run_koru_lane(
        ide,
        instance,
        ["autopilot", "status", "--ide", ide, "--explain"],
    )


def _lane_status(ide: str, instance: str) -> int:
    from coru.cli import _lane_status_raw
    return _lane_status_raw(ide, instance)


def _subprocess_blocked_in_tests() -> bool:
    from coru.cli import _ORIGINAL_SUBPROCESS_RUN
    return (
        ("pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"))
        and subprocess.run is _ORIGINAL_SUBPROCESS_RUN
    )


def _lane_status_env(
    ide: str,
    instance: str,
    resolved: dict[str, Any],
) -> dict[str, str]:
    from coru.cli import _lane_subprocess_env
    env = _lane_subprocess_env(ide, instance)
    resolved_env = resolved.get("env") if isinstance(resolved.get("env"), dict) else {}
    for key, value in resolved_env.items():
        env[str(key)] = str(value)
    if resolved.get("ide"):
        env["KORU_AUTOPILOT_IDE"] = str(resolved["ide"])
    if resolved.get("instance"):
        env["KORU_AUTOPILOT_INSTANCE"] = str(resolved["instance"])
    if resolved.get("socket"):
        env["KORU_AUTOPILOT_SOCKET"] = str(resolved["socket"])
    return env


def _run_lane_status_json(
    koru_exec: list[str],
    ide: str,
    instance: str,
    env: dict[str, str],
) -> dict[str, Any] | None:
    from coru.cli import _LANE_ENV_PAYLOAD_TIMEOUT_S, _project_for_lane
    project = _project_for_lane(ide, instance)
    cmd = [*koru_exec, "autopilot", "status", "--ide", ide, "--json"]
    if project:
        cmd.extend(["--project", project])
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            env=env,
            timeout=_LANE_ENV_PAYLOAD_TIMEOUT_S,
            close_fds=True,
        )
    except (subprocess.TimeoutExpired, Exception):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _lane_status_payload(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    from coru.cli import _koru_autopilot_env_payload, _koru_exec_argv
    if _subprocess_blocked_in_tests():
        return None
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        return None
    resolved = payload or _koru_autopilot_env_payload(ide, instance) or {}
    env = _lane_status_env(ide, instance, resolved)
    return _run_lane_status_json(koru_exec, ide, instance, env)


def _fetch_manage_report(ide: str, instance: str) -> dict[str, Any] | None:
    from coru.cli import _LANE_ENV_PAYLOAD_TIMEOUT_S, _ORIGINAL_SUBPROCESS_RUN, _koru_exec_argv, _lane_subprocess_env
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        if subprocess.run is _ORIGINAL_SUBPROCESS_RUN:
            return None
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        return None
    cmd = [*koru_exec, "autopilot", "manage", "--ide", ide, "--format", "json"]
    env = _lane_subprocess_env(ide, instance)
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False, env=env, timeout=_LANE_ENV_PAYLOAD_TIMEOUT_S, close_fds=True)
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None
    if proc.returncode != 0 and not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _manage_repair_context(
    ide: str,
    instance: str,
) -> tuple[dict[str, Any] | None, bool, str | None, list[repair_registry.RepairProblem]]:
    from coru.cli import _fetch_manage_report
    manage = _fetch_manage_report(ide, instance)
    if not manage:
        return None, False, None, []

    daemon_running = bool(
        isinstance(manage.get("daemon"), dict)
        and manage["daemon"].get("running")
    )
    plugin = manage.get("plugin") if isinstance(manage.get("plugin"), dict) else {}
    expected_build = str(plugin.get("expected_build_sha") or "").strip() or None
    problems = repair_registry.collect_problems_from_manage_report(manage)
    return manage, daemon_running, expected_build, problems


def _drive_result_from_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    drive = payload.get("drive") if isinstance(payload.get("drive"), dict) else None
    if drive is None and payload.get("verification"):
        return payload
    return drive


def _problem_from_readiness_issue(
    issue: Any,
    *,
    source: str,
) -> repair_registry.RepairProblem:
    return repair_registry.RepairProblem(
        code=str(issue.code),
        severity="error" if issue.severity == "fail" else "warning",
        message=str(issue.message),
        fix_hint=str(issue.fix_command) if issue.fix_command else None,
        context={"source": source},
    )


def _runtime_readiness_problems(
    readiness: Any,
    root: Path | None,
) -> list[repair_registry.RepairProblem]:
    if readiness is None or root is None or not hasattr(readiness, "check_runtime_consistency"):
        return []
    runtime = readiness.check_runtime_consistency(root, launcher_executable=sys.executable, strict=False)
    return [
        _problem_from_readiness_issue(issue, source="readiness.runtime")
        for issue in runtime.issues
    ]


def _lane_alignment_problems(
    readiness: Any,
    root: Path | None,
    payload: dict[str, Any] | None,
    *,
    ide: str,
    instance: str,
) -> list[repair_registry.RepairProblem]:
    from coru.cli import _terminal_host_kind, _terminal_shell_context
    if readiness is None or root is None or not payload:
        return []
    socket_raw = str(payload.get("socket") or "").strip()
    if not socket_raw:
        return []

    terminal_ide, _terminal_source, terminal_integrated = _terminal_shell_context()
    lane = readiness.check_lane_terminal_socket_alignment(
        autopilot_ide=ide,
        lane_instance=instance,
        socket_path=Path(socket_raw),
        terminal_ide=terminal_ide,
        terminal_integrated=terminal_integrated,
        terminal_kind=_terminal_host_kind(),
    )
    return [
        _problem_from_readiness_issue(issue, source="readiness.lane_alignment")
        for issue in lane.issues
    ]


def _collect_lane_repair_problems(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None = None,
) -> list[repair_registry.RepairProblem]:
    from coru.cli import _import_koru_readiness_module, _lane_status_payload, _repo_root
    problems: list[repair_registry.RepairProblem] = []
    _manage, daemon_running, expected_build, manage_problems = _manage_repair_context(ide, instance)
    problems.extend(manage_problems)

    status = _lane_status_payload(ide, instance, payload=payload)
    problems.extend(
        repair_registry.collect_problems_from_status(
            status,
            ide=ide,
            expected_build=expected_build,
            daemon_running=daemon_running,
        )
    )
    problems.extend(repair_registry.collect_problems_from_console_logs(status, ide=ide))

    drive = _drive_result_from_payload(payload)
    if isinstance(drive, dict):
        problems.extend(repair_registry.collect_problems_from_drive_result(drive, ide=ide))

    readiness = _import_koru_readiness_module()
    root = _repo_root()
    problems.extend(_runtime_readiness_problems(readiness, root))
    problems.extend(
        _lane_alignment_problems(
            readiness,
            root,
            payload,
            ide=ide,
            instance=instance,
        )
    )
    return repair_registry.dedupe_problems(problems)


def _repair_reload_ide(ide: str, repo_root: Path | None) -> repair_registry.RepairAttempt:
    from coru.cli import _repo_root
    try:
        from koru.ide_adapters.ide_reload import try_reload_vscode_family_ide
    except ImportError as exc:
        return repair_registry.RepairAttempt(
            action_id="reload_ide",
            mode="auto",
            ok=False,
            message=f"koru ide reload unavailable: {exc}",
        )
    project = repo_root if repo_root is not None and repo_root.is_dir() else _repo_root()
    outcome = try_reload_vscode_family_ide(
        ide,
        project=project,
        allow_reuse_window=True,
    )
    return repair_registry.RepairAttempt(
        action_id="reload_ide",
        mode="auto",
        ok=bool(getattr(outcome, "ok", False)),
        message=(
            f"method={getattr(outcome, 'method', None) or '-'} "
            f"detail={getattr(outcome, 'detail', None) or 'ok'}"
        ),
    )


def _repair_connect_plugin(ide: str) -> repair_registry.RepairAttempt:
    try:
        from koru.ide_adapters.ide_reload import connect_via_command_palette
    except ImportError as exc:
        return repair_registry.RepairAttempt(
            action_id="connect_plugin",
            mode="auto",
            ok=False,
            message=f"koru connect palette unavailable: {exc}",
        )
    outcome = connect_via_command_palette(ide)
    return repair_registry.RepairAttempt(
        action_id="connect_plugin",
        mode="auto",
        ok=bool(getattr(outcome, "ok", False)),
        message=(
            f"method={getattr(outcome, 'method', None) or '-'} "
            f"detail={getattr(outcome, 'detail', None) or 'ok'}"
        ),
    )


def _repair_strict_handshake_cycle(ide: str, instance: str) -> repair_registry.RepairAttempt:
    """Restart daemon with strict plugin policy; stale plugins self-reload on rejection."""
    from coru.cli import _run_koru_lane, _start_autopilot_daemon_for_lane
    _run_koru_lane(ide, instance, ["autopilot", "shutdown"])
    time.sleep(0.8)
    rc = _start_autopilot_daemon_for_lane(ide, instance, wait_seconds=5.0, strict_plugin=True)
    return repair_registry.RepairAttempt(
        action_id="strict_handshake_cycle",
        mode="auto",
        ok=rc == 0,
        message="strict daemon restart ok" if rc == 0 else f"strict daemon restart rc={rc}",
    )


def _run_lane_repair(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None = None,
    trigger: str = "coru.repair",
) -> repair_registry.RepairPlan:
    from coru.cli import (
        _ensure_daemon_running,
        _lane_status_payload,
        _repair_connect_plugin,
        _repair_reload_ide,
        _repo_root,
        _run_koru_lane,
    )
    problems = _collect_lane_repair_problems(ide, instance, payload=payload)
    root = _repo_root()
    if root is not None and problems:
        RepairService.for_project(root).record_diagnosis(
            RecordDiagnosisCommand(
                ide=ide,
                instance=instance,
                problems=tuple(problems),
                trigger=f"{trigger}:diagnosis",
                snapshot={"payload_keys": sorted(payload.keys()) if isinstance(payload, dict) else []},
            )
        )
    if not problems:
        return repair_registry.RepairPlan(session_id="", problems=(), attempts=(), resolved=True, trigger=trigger)

    print(f"[coru] repair: detected {len(problems)} issue(s) for ide={ide} instance={instance}", file=sys.stderr)
    plan = repair_registry.run_repair_pipeline(
        ide=ide,
        instance=instance,
        repo_root=root,
        problems=problems,
        trigger=trigger,
        run_koru=lambda args: _run_koru_lane(ide, instance, list(args)),
        replay=lambda lane_ide, lane_instance, args: _run_koru_lane(lane_ide, lane_instance, list(args)),
        fetch_status=lambda lane_ide, lane_instance: _lane_status_payload(
            lane_ide,
            lane_instance,
            payload=payload,
        ),
        ensure_daemon=lambda: _ensure_daemon_running(ide, instance),
        ide_reload=_repair_reload_ide,
        ide_connect=_repair_connect_plugin,
        strict_handshake=lambda: _repair_strict_handshake_cycle(ide, instance),
    )
    for line in repair_registry.format_repair_lines(plan):
        print(line, file=sys.stderr)
    if root is not None:
        store_path = RepairService.for_project(root).store_path
        print(f"[coru] repair: event log → {store_path}", file=sys.stderr)
    return plan


def _running_ide_summary() -> str:
    try:
        from koruide.ide import detect_running_ides

        rows = detect_running_ides()
    except Exception:
        return "unknown"
    if not rows:
        return "none"
    return ", ".join(f"{row.id}(pid={row.pid})" for row in rows[:6])


def _target_plugin_rows(status: dict[str, Any] | None, *, ide: str) -> list[dict[str, Any]]:
    if not isinstance(status, dict):
        return []
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return []
    rows: list[dict[str, Any]] = []
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        plugin_ide = str(plugin.get("ide") or "").strip().lower()
        if plugin_ide == ide:
            rows.append(plugin)
    return rows


def _plugin_workspace_summary(plugin: dict[str, Any]) -> str:
    folders = plugin.get("workspaceFolders")
    if not isinstance(folders, list) or not folders:
        return "workspace=unknown"
    shown = [str(folder) for folder in folders[:2]]
    suffix = ",..." if len(folders) > 2 else ""
    return "workspace=" + ",".join(shown) + suffix


def _print_ide_control_context(
    ide: str,
    instance: str,
    *,
    status: dict[str, Any] | None = None,
    reason: str = "readiness",
    guidance: bool = False,
) -> None:
    from coru.cli import _target_plugin_rows, _terminal_shell_context
    terminal_ide, terminal_source, integrated = _terminal_shell_context()
    print(
        f"[coru] ide context ({reason}): target={ide}/{instance} "
        f"terminal={terminal_ide or 'system'} integrated={'yes' if integrated else 'no'} "
        f"source={terminal_source}",
        file=sys.stderr,
    )
    print(f"[coru] ide context ({reason}): running={_running_ide_summary()}", file=sys.stderr)

    plugins = _target_plugin_rows(status, ide=ide)
    if plugins:
        plugin_bits = "; ".join(
            f"{ide} plugin v{plugin.get('version') or '?'} {_plugin_workspace_summary(plugin)}"
            for plugin in plugins[:3]
        )
        print(f"[coru] ide context ({reason}): plugin=connected {plugin_bits}", file=sys.stderr)
    else:
        print(f"[coru] ide context ({reason}): plugin=missing target={ide}", file=sys.stderr)

    if not guidance:
        return

    if not plugins:
        print(
            f"[coru] next: open {ide} on this project and run Command Palette command "
            "`koru: Connect autopilot daemon`",
            file=sys.stderr,
        )
        print(
            "[coru] next: if the extension is stale, run `Developer: Reload Window` "
            "and connect the plugin again",
            file=sys.stderr,
        )
    if integrated and terminal_ide and terminal_ide != ide and not plugins:
        print(
            f"[coru] next: current terminal belongs to {terminal_ide}; "
            f"for strict plugin control, rerun from {ide}'s integrated terminal",
            file=sys.stderr,
        )
    print(
        f"[coru] next: keep {ide}'s chat/composer visible; if submit stalls, "
        "place the text cursor in the chat input and press Enter/Send",
        file=sys.stderr,
    )


def _lane_doctor(
    ide: str,
    instance: str,
    *,
    fix: bool = False,
    probe: bool = False,
    probe_prompt: str = "test",
    skip_ensure: bool = False,
) -> int:
    from coru.cli import (
        _diagnose_lane,
        _fetch_drive_payload,
        _koru_autopilot_env_payload,
        _lane_chat_prompt,
        _lane_status_raw,
        _run_koru_lane,
        _run_lane_repair,
    )
    rc = _diagnose_lane(ide, instance, skip_ensure=skip_ensure)
    if rc != 0 and not fix:
        return rc

    if fix:
        print("[coru] doctor: bridge repair (registry pipeline)...")
        payload = _koru_autopilot_env_payload(ide, instance)
        repair_plan = _run_lane_repair(ide, instance, payload=payload, trigger="coru.doctor")
        if not repair_plan.resolved:
            print(
                "[coru] doctor: registry repair incomplete; "
                "running fallback koru ide doctor --fix...",
                file=sys.stderr,
            )
            fix_rc = _run_koru_lane(
                ide,
                instance,
                ["ide", "doctor", "--ide", ide, "--fix", "--gc-sockets", "--explain"],
            )
            if fix_rc != 0:
                return fix_rc
        rc = _lane_status_raw(ide, instance)

    if probe:
        print(f"[coru] doctor: plugin-required drive probe (prompt={probe_prompt!r})...")
        probe_rc = _lane_chat_prompt(ide, instance, probe_prompt, require_plugin=True)
        if probe_rc != 0:
            drive_payload = _fetch_drive_payload(ide, instance, probe_prompt, require_plugin=True)
            if drive_payload:
                payload = _koru_autopilot_env_payload(ide, instance) or {}
                payload = {**payload, "drive": drive_payload}
                _run_lane_repair(ide, instance, payload=payload, trigger="coru.doctor.probe")
            return probe_rc

    return rc


def _refactor_intent(text: str) -> bool:
    from coru.cli import _REFACTOR_MARKERS
    t = text.strip().lower()
    if any(m in t for m in _REFACTOR_MARKERS):
        return True
    return re.search(r"refak\w*ryz", t) is not None


def _lane_auto(ide: str, instance: str, extra_args: Sequence[str]) -> int:
    from coru.cli import _koru_exec_argv, _project_for_lane, _run_koru_lane
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127

    auto_args = list(extra_args)
    if not any(token == "--agent-lane" or token.startswith("--agent-lane=") for token in auto_args):
        auto_args = ["--agent-lane", instance, *auto_args]
    project = _project_for_lane(ide, instance)
    if project and not any(token == "--project" or token.startswith("--project=") for token in auto_args):
        auto_args = ["--project", project, *auto_args]
    return _run_koru_lane(ide, instance, ["auto", *auto_args])


def _env_enabled(name: str, *, default: bool = True) -> bool:
    from coru.cli import _FALSE_ENV_VALUES
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSE_ENV_VALUES


def _gc_stale_lane_socket(ide: str, instance: str) -> int:
    from coru.cli import _run_koru_lane
    print("[coru] readiness: checking stale daemon/socket state...", file=sys.stderr)
    return _run_koru_lane(
        ide,
        instance,
        ["ide", "doctor", "--ide", ide, "--fix", "--gc-sockets", "--explain"],
    )


def _check_lane_status_and_ownership(
    ide: str,
    instance: str,
    payload: dict[str, Any] | None,
) -> tuple[int, str]:
    """Return (rc, reason) after checking lane status, self-heal, and ownership."""
    from coru.cli import (
        _attempt_plugin_self_heal,
        _auto_ownership_gate,
        _lane_status_payload,
        _lane_status_raw,
        _print_ide_control_context,
    )
    status_rc = _lane_status_raw(ide, instance)
    if status_rc == 0:
        ownership_rc = _auto_ownership_gate(ide, instance, payload=payload)
        return ownership_rc, "ownership" if ownership_rc != 0 else ""

    heal_rc = _attempt_plugin_self_heal(ide, instance)
    if heal_rc == 0:
        status_rc = _lane_status_raw(ide, instance)

    if status_rc == 0:
        ownership_rc = _auto_ownership_gate(ide, instance, payload=payload)
        if ownership_rc != 0:
            return ownership_rc, "ownership"

    if status_rc != 0:
        _print_ide_control_context(
            ide,
            instance,
            status=_lane_status_payload(ide, instance, payload=payload),
            reason="plugin",
            guidance=True,
        )
    return status_rc, "plugin" if status_rc != 0 else ""
