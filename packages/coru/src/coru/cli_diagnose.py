"""Daemon startup, runtime diagnostics and LLM chat prompt rewriting extracted from ``coru.cli``."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from coru import repair_registry

def _koru_exec_argv() -> list[str] | None:
    from coru.cli import _binary_path, _local_module_source_dir, _python_module_exists
    binary_path = _binary_path("koru")
    if binary_path is not None:
        return [binary_path]
    if _python_module_exists("koru.cli"):
        return [sys.executable, "-m", "koru.cli"]
    local_source = _local_module_source_dir("koru.cli")
    if local_source is not None:
        runner = (
            "import sys; "
            f"sys.path.insert(0, {str(local_source)!r}); "
            "from koru.cli import main; "
            "raise SystemExit(main(sys.argv[1:]))"
        )
        return [sys.executable, "-c", runner]
    return None


def _fetch_drive_payload(
    ide: str,
    instance: str,
    prompt: str,
    *,
    require_plugin: bool = True,
) -> dict[str, Any] | None:
    from coru.cli import (
        _CALIBRATION_DRIVE_TIMEOUT_S,
        _koru_exec_argv,
        _lane_subprocess_env,
        _parse_drive_json_from_stdout,
    )
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        return None
    cmd = [
        *koru_exec,
        "autopilot",
        "drive",
        "--ide",
        ide,
        "--prompt",
        prompt,
    ]
    if require_plugin:
        cmd.append("--require-plugin")
    env = _lane_subprocess_env(ide, instance)
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            env=env,
            timeout=_CALIBRATION_DRIVE_TIMEOUT_S,
            close_fds=True,
        )
    except Exception:
        return None
    raw = (proc.stdout or "").strip()
    return _parse_drive_json_from_stdout(raw)


def _lane_chat_prompt(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
    from coru.cli import _koru_exec_argv, _run_koru_lane
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127

    drive_args = ["autopilot", "drive", "--ide", ide]
    if require_plugin:
        drive_args.append("--require-plugin")
    drive_args.append(prompt)
    return _run_koru_lane(ide, instance, drive_args)


def _start_autopilot_daemon_for_lane(
    ide: str,
    instance: str,
    *,
    wait_seconds: float = 5.0,
    strict_plugin: bool = False,
) -> int:
    from coru.cli import (
        _apply_strict_plugin_policy_defaults,
        _koru_autopilot_env_payload,
        _koru_exec_argv,
        _project_for_lane,
    )
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127

    payload = _koru_autopilot_env_payload(ide, instance)
    env = dict(os.environ)
    if payload and payload.get("env"):
        env.update({str(k): str(v) for k, v in payload["env"].items()})
    else:
        env["KORU_AUTOPILOT_IDE"] = ide
        env["KORU_AUTOPILOT_INSTANCE"] = instance
        env.pop("KORU_AUTOPILOT_SOCKET", None)
    if strict_plugin:
        _apply_strict_plugin_policy_defaults(env, force=True)

    cmd = [*koru_exec, "autopilot", "daemon", "--idempotent"]
    project = _project_for_lane(ide, instance)
    if project:
        cmd.extend(["--project", project])
    try:
        subprocess.Popen(
            cmd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except KeyboardInterrupt:
        return 130
    except Exception:
        return 1

    socket_path = (payload or {}).get("socket")
    if not socket_path:
        time.sleep(0.2)
        return 0

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if Path(str(socket_path)).exists():
            return 0
        time.sleep(0.2)
    return 0


def _ensure_daemon_running(ide: str, instance: str, *, wait_seconds: float = 15.0) -> int:
    from coru.cli import _lane_status_raw, _start_autopilot_daemon_for_lane
    if _lane_status_raw(ide, instance) == 0:
        return 0

    print(
        f"[coru] autopilot daemon not ready; starting idempotent daemon "
        f"for ide={ide} instance={instance}",
        file=sys.stderr,
    )
    start_rc = _start_autopilot_daemon_for_lane(ide, instance, wait_seconds=min(wait_seconds, 5.0))
    if start_rc != 0:
        return start_rc

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if _lane_status_raw(ide, instance) == 0:
            return 0
        time.sleep(0.5)

    print(
        "[coru] daemon may be up but bridge is not ready; "
        "run 'coru daemon' in a system terminal and connect the plugin in the IDE",
        file=sys.stderr,
    )
    return 1


def _import_koru_readiness_module() -> Any | None:
    from coru.cli import _repo_root
    for root in (_repo_root(),):
        if root is None:
            continue
        src = root / "src"
        if not src.is_dir() or not (src / "koru").is_dir():
            continue
        src_s = str(src.resolve())
        if src_s not in sys.path:
            sys.path.insert(0, src_s)
    try:
        from koru import autonomous_readiness as readiness

        return readiness
    except ImportError:
        return None


def _diagnose_readiness_alignment(
    *,
    root: Path | None,
    ide: str,
    instance: str,
    strict: bool,
) -> int | None:
    from coru.cli import _import_koru_readiness_module, _terminal_shell_context
    readiness = _import_koru_readiness_module()
    if root is None or readiness is None:
        return None

    result = readiness.check_runtime_consistency(
        root,
        launcher_executable=sys.executable,
        strict=strict,
    )
    for line in readiness.format_readiness_lines(result, prefix="[coru]"):
        print(line, file=sys.stderr)

    terminal_ide, _terminal_source, terminal_integrated = _terminal_shell_context()
    lane = readiness.check_lane_terminal_socket_alignment(
        autopilot_ide=ide,
        lane_instance=instance,
        socket_path=None,
        terminal_ide=terminal_ide,
        terminal_integrated=terminal_integrated,
    )
    for line in readiness.format_readiness_lines(lane, prefix="[coru]"):
        print(line, file=sys.stderr)

    if strict and not (result.ok and lane.ok):
        fix = result.primary_fix or lane.primary_fix
        if fix:
            print(f"[coru] readiness fail-fast: {fix}", file=sys.stderr)
        return 1
    if not result.ok:
        return 0
    return None


def _warn_python_env_mismatch() -> None:
    from coru.cli import _project_venv_python
    project_python = _project_venv_python()
    current_python = str(Path(sys.executable).resolve())
    if project_python:
        project_python = str(Path(project_python).resolve())
    if project_python and current_python != project_python:
        print(
            "[coru] warning: python env mismatch: "
            f"active={current_python} repo_venv={project_python}; "
            "prefer repo .venv to keep daemon/plugin versions aligned",
            file=sys.stderr,
        )


def _warn_koru_exec_outside_repo(root_s: str) -> None:
    from coru.cli import _koru_exec_argv
    koru_exec = _koru_exec_argv() or []
    if not (koru_exec and root_s and os.path.isabs(koru_exec[0])):
        return

    koru_exec_path = str(Path(koru_exec[0]).resolve())
    if not koru_exec_path.startswith(root_s):
        print(
            "[coru] warning: koru executable is outside repo: "
            f"{koru_exec_path} (repo={root_s})",
            file=sys.stderr,
        )


def _warn_lane_project_mismatch(payload: dict[str, Any] | None, root_s: str) -> None:
    if not (payload and root_s):
        return

    payload_project = str(payload.get("project") or "").strip()
    if not payload_project:
        return

    try:
        payload_resolved = str(Path(payload_project).resolve())
    except Exception:
        payload_resolved = payload_project
    if payload_resolved != root_s:
        print(
            "[coru] warning: lane project differs from current repo: "
            f"lane_project={payload_resolved} repo={root_s}",
            file=sys.stderr,
        )


def _diagnose_runtime_consistency(ide: str, instance: str, payload: dict[str, Any] | None) -> int:
    from coru.cli import _coru_readiness_strict, _repo_root
    root = _repo_root()
    root_s = str(root.resolve()) if root is not None else ""
    readiness_rc = _diagnose_readiness_alignment(
        root=root,
        ide=ide,
        instance=instance,
        strict=_coru_readiness_strict(),
    )
    if readiness_rc is not None:
        return readiness_rc

    _warn_python_env_mismatch()
    _warn_koru_exec_outside_repo(root_s)
    _warn_lane_project_mismatch(payload, root_s)
    return 0


def _attempt_plugin_self_heal(
    ide: str,
    instance: str,
    *,
    timeout_seconds: float = 12.0,
    attempts: int = 3,
) -> int:
    from coru.cli import (
        _fetch_manage_report,
        _import_koru_readiness_module,
        _lane_status_payload,
        _lane_status_raw,
        _repair_connect_plugin,
        _repair_reload_ide,
        _repo_root,
        _run_koru_lane,
    )
    print(
        "[coru] plugin self-heal: attempting IDE reload and plugin reconnect "
        f"for ide={ide} instance={instance}",
        file=sys.stderr,
    )

    readiness = _import_koru_readiness_module()
    if readiness is not None:

        def _reload() -> bool:
            attempt = _repair_reload_ide(ide, _repo_root())
            print(f"[coru] plugin self-heal: {attempt.message}", file=sys.stderr)
            if attempt.ok:
                time.sleep(5.0)
            return attempt.ok

        def _wait(timeout: float) -> bool:
            manage = _fetch_manage_report(ide, instance)
            plugin = manage.get("plugin") if isinstance(manage, dict) and isinstance(manage.get("plugin"), dict) else {}
            expected_build = str(plugin.get("expected_build_sha") or "").strip() or None
            deadline = time.monotonic() + max(0.0, timeout)
            while time.monotonic() < deadline:
                status = _lane_status_payload(ide, instance)
                if repair_registry.plugin_build_aligned(status, ide=ide, expected_build=expected_build):
                    return True
                if expected_build is None and _lane_status_raw(ide, instance) == 0:
                    return True
                time.sleep(0.5)
            return False

        if readiness.run_plugin_reconnect_pipeline(
            reload_window=_reload,
            wait_connected=_wait,
            attempts=attempts,
            base_timeout_seconds=timeout_seconds,
        ):
            return 0
        connect = _repair_connect_plugin(ide)
        print(f"[coru] plugin self-heal connect: {connect.message}", file=sys.stderr)
        if connect.ok and _wait(timeout_seconds):
            return 0
        return 1

    # Replay actions are the orchestrated, auditable control path for IDE actions.
    for attempt in range(1, max(1, attempts) + 1):
        if _lane_status_raw(ide, instance) == 0:
            return 0
        reload_rc = _run_koru_lane(ide, instance, ["replay", f"ide reload-window {ide}"])
        connect_rc = _run_koru_lane(ide, instance, ["replay", f"ide connect-plugin {instance}"])
        if reload_rc != 0 and connect_rc != 0:
            continue
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if _lane_status_raw(ide, instance) == 0:
                return 0
            time.sleep(0.8)
        if attempt < attempts:
            time.sleep(min(1.5 * attempt, 3.0))
    return 1


def _resolve_diagnose_lane(
    ide: str,
    instance: str,
) -> tuple[str, str, dict[str, Any] | None]:
    from coru.cli import _koru_autopilot_env_payload
    payload = _koru_autopilot_env_payload(ide, instance)
    if not payload:
        print("[coru] lane env: koru autopilot env unavailable; using coru lane defaults", file=sys.stderr)
        return ide, instance, payload
    resolved_ide = str(payload.get("ide") or ide)
    resolved_instance = str(payload.get("instance") or instance)
    print(
        f"[coru] lane resolved: ide={resolved_ide} instance={resolved_instance} "
        f"socket={payload.get('socket')} source={payload.get('source')}"
    )
    return resolved_ide, resolved_instance, payload


def _diagnose_lane_status(
    ide: str,
    instance: str,
    *,
    payload: dict[str, Any] | None,
) -> int:
    from coru.cli import _attempt_plugin_self_heal, _lane_status_raw
    status_rc = _lane_status_raw(ide, instance)
    if status_rc == 0:
        return 0
    if _attempt_plugin_self_heal(ide, instance) == 0:
        return _lane_status_raw(ide, instance)
    print(
        "[coru] plugin self-heal did not complete; run in IDE: "
        "Developer: Reload Window, then koru: Connect autopilot daemon",
        file=sys.stderr,
    )
    return status_rc


def _diagnose_lane(
    ide: str,
    instance: str,
    *,
    probe_drive: bool = False,
    skip_ensure: bool = False,
) -> int:
    from coru.cli import (
        _diagnose_runtime_consistency,
        _ensure_commands,
        _ensure_daemon_running,
        _env_enabled,
        _lane_chat_prompt,
        _lane_manage_fix,
        _lane_status_payload,
        _print_ide_control_context,
        _print_troubleshooting_log_locations,
        _run_lane_repair,
        _terminal_shell_context,
    )
    print(f"[coru] diagnose ide={ide} instance={instance}")
    _print_troubleshooting_log_locations(ide, instance)
    _terminal_shell_context()

    if not skip_ensure:
        ensure_rc = _ensure_commands(install=False)
        if ensure_rc != 0:
            return ensure_rc

    ide, instance, payload = _resolve_diagnose_lane(ide, instance)
    if _diagnose_runtime_consistency(ide, instance, payload) != 0:
        return 1

    manage_rc = _lane_manage_fix(ide, instance)
    if manage_rc != 0:
        print("[coru] manage --fix reported issues (continuing)", file=sys.stderr)

    daemon_rc = _ensure_daemon_running(ide, instance)
    if daemon_rc != 0:
        print("[coru] hint: keep `coru daemon` running in a system terminal window", file=sys.stderr)
        print("[coru] hint: in Cursor run command `koru: Connect autopilot daemon` once", file=sys.stderr)

    if _env_enabled("CORU_AUTO_REPAIR", default=False):
        _run_lane_repair(ide, instance, payload=payload, trigger="coru.diagnose")

    if daemon_rc != 0:
        return daemon_rc

    status_rc = _diagnose_lane_status(ide, instance, payload=payload)
    _print_ide_control_context(
        ide,
        instance,
        status=_lane_status_payload(ide, instance, payload=payload),
        reason="diagnose",
        guidance=status_rc != 0,
    )
    if status_rc != 0:
        return status_rc

    if probe_drive:
        print("[coru] probe: koru autopilot drive --require-plugin (prompt=test)")
        return _lane_chat_prompt(ide, instance, "test", require_plugin=True)
    return 0


def _print_troubleshooting_log_locations(ide: str, instance: str) -> None:
    from coru.cli import _repo_root
    root = _repo_root() or Path.cwd()
    plan_dir = root / ".planfile" / ".koru"
    xdg_runtime = (os.environ.get("XDG_RUNTIME_DIR") or "").strip()
    daemon_meta = plan_dir / f"koru-autopilot-{instance}.daemon.json"
    nfo_log = plan_dir / "nfo-events.jsonl"
    audit_log = Path.home() / ".local" / "state" / "koru" / "autopilot.log"
    repair_log = plan_dir / "repair-events.jsonl"
    events_log = (
        Path(xdg_runtime) / "koru-autopilot-events.ndjson"
        if xdg_runtime
        else Path("/tmp/koru-autopilot-events.ndjson")
    )
    print("debug logs:")
    print(f"- repair event log (CQRS/ES): {repair_log}")
    print(f"- daemon audit: {audit_log}")
    print(f"- daemon metadata: {daemon_meta}")
    print(f"- autonomous nfo events: {nfo_log}")
    print(f"- plugin runtime events: {events_log}")
    print(f"- quick check: coru status")
    print(f"- foreground daemon: coru daemon")


def _chat_llm_enabled(use_llm: bool) -> bool:
    return use_llm or bool((os.environ.get("OPENROUTER_API_KEY") or "").strip())


def _llm_rewrite_chat_prompt(text: str, *, ide: str, instance: str) -> str:
    try:
        from nlp2coru.rewrite import rewrite_chat_prompt
    except Exception:
        return text
    model = os.environ.get("CORU_LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    return rewrite_chat_prompt(text, ide=ide, instance=instance, model=model)
