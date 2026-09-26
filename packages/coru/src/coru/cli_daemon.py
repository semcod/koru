

from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from coru.cli import SessionContext
_KORU_SUBPROCESS_TIMEOUT_S = float(os.environ.get("CORU_KORU_SUBPROCESS_TIMEOUT_S", "20"))

def _supervisor_lane_defaults() -> tuple[str, str] | None:
    try:
        from coru.supervisor.paths import registry_path
        from coru.supervisor.registry import active_lane_pair

        if not registry_path().is_file():
            return None
        return active_lane_pair()
    except Exception:
        return None


def _supervisor_lane_project(instance: str | None = None) -> str | None:
    try:
        from coru.supervisor.paths import registry_path
        from coru.supervisor.registry import load_registry

        if not registry_path().is_file():
            return None
        registry = load_registry()
        key = instance or registry.active_lane
        if not key:
            return None
        record = registry.lanes.get(key)
        if record is None or not record.project:
            return None
        project_path = Path(record.project).expanduser()
        if not project_path.is_dir():
            return None
        return str(project_path.resolve())
    except Exception:
        return None


@functools.lru_cache(maxsize=None)
def _is_lane_plugin_connected(ide: str, instance: str) -> bool:
    from coru.cli import _ORIGINAL_SUBPROCESS_RUN, _lane_status_payload, _trace
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        if subprocess.run is _ORIGINAL_SUBPROCESS_RUN:
            return False
    status = _lane_status_payload(ide, instance)
    if not status or not isinstance(status, dict):
        connected = False
    else:
        plugins = status.get("plugins")
        rejected = status.get("rejected_plugins")
        has_plugins = bool(plugins) and isinstance(plugins, list) and len(plugins) > 0
        has_rejected = bool(rejected) and isinstance(rejected, list) and len(rejected) > 0
        connected = has_plugins or has_rejected
    _trace("is_lane_plugin_connected", ide=ide, instance=instance, connected=connected)
    return connected


def _connected_daemon_instance(ide: str) -> str | None:
    from coru.cli import _alive_daemon_instance
    instance = _alive_daemon_instance(ide)
    if not instance:
        return None
    if _is_lane_plugin_connected(ide, instance):
        return instance
    return None


def _connected_daemon_from_meta(path: Path) -> tuple[str, str, float] | None:
    from coru.cli import _ide_from_instance, _instance_from_socket_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    pid = payload.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    instance = _instance_from_socket_path(str(payload.get("socket", "")))
    if not instance:
        instance = (payload.get("env") or {}).get("KORU_AUTOPILOT_INSTANCE", "")
    if not instance:
        return None
    ide = _ide_from_instance(instance)
    if not ide or not _is_lane_plugin_connected(ide, instance):
        return None
    return ide, instance, path.stat().st_mtime


def _alive_daemon_ide() -> str | None:
    """Check .planfile/.koru/koru-autopilot-*.daemon.json for a live daemon."""
    from coru.cli import _runtime_metadata_roots, _trace
    best_connected: tuple[str, str, float] | None = None  # (ide, instance, mtime)
    for root in _runtime_metadata_roots():
        rt = root / ".planfile" / ".koru"
        if not rt.is_dir():
            continue
        for path in sorted(rt.glob("koru-autopilot-*.daemon.json")):
            candidate = _connected_daemon_from_meta(path)
            if candidate is None:
                continue
            ide, instance, mtime = candidate
            if best_connected is None or mtime > best_connected[2]:
                best_connected = (ide, instance, mtime)
    if best_connected is None:
        return None
    _trace("alive_daemon", ide=best_connected[0], instance=best_connected[1])
    return best_connected[0]


def _prefer_terminal_over_lane(hint: str | None, lane_ide: str) -> bool:
    return bool(hint and hint != lane_ide and hint != "vscode")


def _warn_integrated_terminal_daemon_mismatch(hint: str) -> None:
    from coru.cli import _alive_daemon_ide, _connected_daemon_instance, _trace
    if _connected_daemon_instance(hint):
        return
    alive_ide = _alive_daemon_ide()
    if not alive_ide or alive_ide == hint:
        return
    _trace(
        "infer_ide.daemon_mismatch",
        terminal=hint,
        alive_daemon=alive_ide,
        reason="terminal IDE has no connected daemon; keeping terminal IDE",
    )
    print(
        f"[coru] integrated terminal IDE={hint} has no connected daemon "
        f"(alive daemon: {alive_ide}). "
        f"Connect the plugin in {hint}, or pass an explicit lane "
        f"(e.g. `coru calibration {hint}` / KORU_AUTOPILOT_INSTANCE={hint}).",
        file=sys.stderr,
    )


def _integrated_terminal_default_ide(hint: str | None, *, integrated: bool) -> str | None:
    from coru.cli import _trace
    if not integrated or not hint or hint == "auto":
        return None
    _warn_integrated_terminal_daemon_mismatch(hint)
    _trace("infer_ide.result", ide=hint, reason="integrated_terminal")
    return hint


def _project_settings_default_ide(hint: str | None) -> str | None:
    from coru.cli import _project_ide_settings_lane, _trace
    if hint and _project_ide_settings_lane(hint) is not None:
        _trace("infer_ide.result", ide=hint, reason="project_settings")
        return hint
    return None


def _supervisor_default_ide(hint: str | None) -> str | None:
    from coru.cli import _trace
    supervisor = _supervisor_lane_defaults()
    if supervisor is None:
        return None
    if _prefer_terminal_over_lane(hint, supervisor[0]):
        _trace("infer_ide.result", ide=hint, reason="terminal_over_supervisor")
        return hint
    _trace("infer_ide.result", ide=supervisor[0], reason="supervisor")
    return supervisor[0]


def _env_default_ide(hint: str | None, workspace_ide: str | None) -> str | None:
    from coru.cli import _ide_from_instance, _trace
    env_ide = (os.environ.get("KORU_AUTOPILOT_IDE") or "").strip().lower()
    if env_ide and env_ide != "auto":
        if _prefer_terminal_over_lane(hint, env_ide):
            _trace("infer_ide.result", ide=hint, reason="terminal_over_env")
            return hint
        _trace("infer_ide.result", ide=env_ide, reason="env:KORU_AUTOPILOT_IDE")
        return env_ide
    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip().lower()
    from_instance = _ide_from_instance(env_instance)
    if from_instance:
        if _prefer_terminal_over_lane(hint, from_instance):
            _trace("infer_ide.result", ide=hint, reason="terminal_over_instance")
            return hint
        _trace("infer_ide.result", ide=from_instance, reason="env:KORU_AUTOPILOT_INSTANCE")
        return from_instance
    if hint:
        _trace("infer_ide.result", ide=hint, reason="terminal_fallback")
        return hint
    if workspace_ide:
        _trace("infer_ide.result", ide=workspace_ide, reason="workspace_settings")
        return workspace_ide
    return None


def _infer_default_ide() -> str:
    from coru.cli import _terminal_ide_hint, _terminal_shell_context, _trace, _workspace_lane_hint
    hint = _terminal_ide_hint()
    _term_ide, _term_source, integrated = _terminal_shell_context()
    _trace("infer_ide.start", terminal_hint=hint, integrated=integrated, source=_term_source)
    for resolver in (
        lambda: _integrated_terminal_default_ide(hint, integrated=integrated),
        lambda: _project_settings_default_ide(hint),
        lambda: _supervisor_default_ide(hint),
        lambda: _env_default_ide(hint, _workspace_lane_hint(hint)[0]),
    ):
        ide = resolver()
        if ide:
            return ide
    _trace("infer_ide.result", ide="auto", reason="no_signal")
    return "auto"


def _project_ide_settings_instance(ide: str) -> str | None:
    from coru.cli import _project_ide_settings_lane
    settings_lane = _project_ide_settings_lane(ide)
    if settings_lane is not None:
        return settings_lane[1]
    return None


def _supervisor_default_instance(ide: str) -> str | None:
    from coru.cli import _terminal_ide_hint
    supervisor = _supervisor_lane_defaults()
    if supervisor is None:
        return None
    sup_ide, sup_instance = supervisor
    terminal = _terminal_ide_hint()
    if terminal and terminal != sup_ide and terminal != "vscode":
        if ide == "auto" or ide == terminal:
            terminal_settings = _project_ide_settings_instance(terminal)
            if terminal_settings is not None:
                return terminal_settings
            return terminal
    if ide == "auto" or sup_ide == ide:
        return sup_instance
    return None


def _environment_default_instance(ide: str) -> str | None:
    from coru.cli import _ide_from_instance, _instance_matches_ide
    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    if not env_instance or env_instance.lower() == "auto":
        return None
    if ide == "auto":
        # Ignore generic "main" when IDE is unknown; prefer terminal-derived lane.
        if _ide_from_instance(env_instance):
            return env_instance
        return None
    if _instance_matches_ide(env_instance, ide):
        return env_instance
    return None


def _auto_default_instance() -> str:
    from coru.cli import _terminal_ide_hint, _workspace_lane_hint
    terminal = _terminal_ide_hint()
    if terminal:
        terminal_settings = _project_ide_settings_instance(terminal)
        if terminal_settings is not None:
            return terminal_settings
        return terminal
    _workspace_ide, workspace_instance = _workspace_lane_hint(None)
    if workspace_instance:
        return workspace_instance
    return "main"


def _workspace_default_instance(ide: str) -> str | None:
    from coru.cli import _workspace_lane_hint
    workspace_ide, workspace_instance = _workspace_lane_hint(ide)
    if workspace_instance:
        if workspace_ide == ide:
            return workspace_instance
    return None


def _infer_default_instance(*, ide: str) -> str:
    from coru.cli import _trace
    _trace("infer_instance.start", ide=ide)
    sources = [
        ("project_settings", _project_ide_settings_instance(ide)),
        ("supervisor", _supervisor_default_instance(ide)),
        ("environment", _environment_default_instance(ide)),
    ]
    for source_name, candidate in sources:
        if candidate is not None:
            _trace("infer_instance.result", instance=candidate, reason=source_name)
            return candidate

    if ide == "auto":
        result = _auto_default_instance()
        _trace("infer_instance.result", instance=result, reason="auto_default")
        return result

    workspace_instance = _workspace_default_instance(ide)
    if workspace_instance is not None:
        _trace("infer_instance.result", instance=workspace_instance, reason="workspace")
        return workspace_instance

    if ide and ide != "auto":
        _trace("infer_instance.result", instance=ide, reason="ide_as_instance")
        return ide
    _trace("infer_instance.result", instance="main", reason="fallback")
    return "main"


def _maybe_warn_lane_override(ide: str, instance: str, *, context: SessionContext | None = None) -> None:
    from coru.cli import _ide_from_instance
    if context is not None and context.lane_override_warned:
        return

    env_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
    if not env_instance or env_instance == instance:
        return

    env_ide = _ide_from_instance(env_instance)
    should_warn = env_instance.lower() in {"main", "auto"} or (env_ide is not None and env_ide != ide)
    if not should_warn:
        return

    print(f"[coru] stale lane overridden: {env_instance} -> {instance}", file=sys.stderr)
    if context is not None:
        context.lane_override_warned = True


@contextmanager
def _bind_lane_session(ide: str, instance: str):
    from coru.cli import _LANE_SESSION_ENV_KEYS, _apply_strict_plugin_policy_defaults
    previous = {key: os.environ[key] for key in _LANE_SESSION_ENV_KEYS if key in os.environ}
    os.environ["KORU_AUTOPILOT_IDE"] = ide
    os.environ["KORU_AUTOPILOT_INSTANCE"] = instance
    os.environ.pop("KORU_AUTOPILOT_SOCKET", None)
    _apply_strict_plugin_policy_defaults(os.environ)
    try:
        yield
    finally:
        for key in _LANE_SESSION_ENV_KEYS:
            if key in previous:
                os.environ[key] = previous[key]
            else:
                os.environ.pop(key, None)


def _run_with_lane_environment(
    command: Sequence[str],
    *,
    ide: str,
    instance: str,
    timeout: float | None = _KORU_SUBPROCESS_TIMEOUT_S,
) -> int:
    from coru.cli import _LANE_SESSION_ENV_KEYS, _apply_strict_plugin_policy_defaults, _run
    previous = {key: os.environ[key] for key in _LANE_SESSION_ENV_KEYS if key in os.environ}
    try:
        os.environ["KORU_AUTOPILOT_IDE"] = ide
        os.environ["KORU_AUTOPILOT_INSTANCE"] = instance
        os.environ.pop("KORU_AUTOPILOT_SOCKET", None)
        _apply_strict_plugin_policy_defaults(os.environ)
        return _run(command, timeout=timeout)
    finally:
        for key in _LANE_SESSION_ENV_KEYS:
            if key in previous:
                os.environ[key] = previous[key]
            else:
                os.environ.pop(key, None)


def _koru_autopilot_env_payload(ide: str, instance: str) -> dict[str, Any] | None:
    from coru.cli import (
        _LANE_ENV_PAYLOAD_TIMEOUT_S,
        _ORIGINAL_SUBPROCESS_RUN,
        _koru_exec_argv,
        _lane_subprocess_env,
        _project_for_lane,
    )
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        if subprocess.run is _ORIGINAL_SUBPROCESS_RUN:
            return None
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        return None
    project = _project_for_lane(ide, instance)
    cmd = [*koru_exec, "autopilot", "env", "--ide", ide, "--format", "json"]
    if project:
        cmd.extend(["--project", project])
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            env=_lane_subprocess_env(ide, instance),
            timeout=_LANE_ENV_PAYLOAD_TIMEOUT_S,
            close_fds=True,
        )
    except subprocess.TimeoutExpired:
        print(
            f"[coru] koru autopilot env timed out after {_LANE_ENV_PAYLOAD_TIMEOUT_S:.0f}s "
            f"(ide={ide} instance={instance})",
            file=sys.stderr,
        )
        return None
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return None
    if not isinstance(payload, dict) or not payload.get("ok"):
        return None
    return payload


def _run_with_resolved_lane_env(
    command: Sequence[str],
    *,
    ide: str,
    instance: str,
    timeout: float | None = _KORU_SUBPROCESS_TIMEOUT_S,
) -> int:
    from coru.cli import (
        _LANE_SESSION_ENV_KEYS,
        _apply_strict_plugin_policy_defaults,
        _koru_autopilot_env_payload,
        _run,
    )
    payload = _koru_autopilot_env_payload(ide, instance)
    if not payload:
        if timeout is None:
            return _run(list(command))
        return _run_with_lane_environment(command, ide=ide, instance=instance, timeout=timeout)

    previous = {key: os.environ[key] for key in _LANE_SESSION_ENV_KEYS if key in os.environ}
    resolved_env = payload.get("env") or {}
    try:
        for key, value in resolved_env.items():
            os.environ[str(key)] = str(value)
        if payload.get("instance"):
            os.environ["KORU_AUTOPILOT_INSTANCE"] = str(payload["instance"])
        if payload.get("ide"):
            os.environ["KORU_AUTOPILOT_IDE"] = str(payload["ide"])
        _apply_strict_plugin_policy_defaults(os.environ)
        return _run(command, timeout=timeout)
    finally:
        for key in _LANE_SESSION_ENV_KEYS:
            if key in previous:
                os.environ[key] = previous[key]
            else:
                os.environ.pop(key, None)


def _run_koru_lane(ide: str, instance: str, koru_args: Sequence[str]) -> int:
    from coru.cli import _koru_exec_argv, _koru_subprocess_timeout, _run_with_resolved_lane_env
    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run_with_resolved_lane_env(
        [*koru_exec, *koru_args],
        ide=ide,
        instance=instance,
        timeout=_koru_subprocess_timeout(koru_args),
    )


def _koruenv_run_fallback(ide: str, instance: str, run_payload: Sequence[str]) -> int:
    from coru.cli import _tool_argv
    try:
        cmd = _tool_argv("koruenv", "koruenv.cli", ["run", ide, instance, *run_payload])
    except FileNotFoundError:
        print("error: koruenv is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run_with_lane_environment(cmd, ide=ide, instance=instance)


def _lane_env(ide: str, instance: str, shell: str) -> int:
    from coru.cli import _koru_exec_argv, _project_for_lane, _run_koru_lane, _tool_argv
    if _koru_exec_argv() is not None:
        args = ["autopilot", "env", "--ide", ide]
        project = _project_for_lane(ide, instance)
        if project:
            args.extend(["--project", project])
        return _run_koru_lane(ide, instance, args)
    try:
        argv = _tool_argv("koruenv", "koruenv.cli", ["env", ide, instance, "--shell", shell])
    except FileNotFoundError:
        print("error: koruenv is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127
    return _run_with_lane_environment(argv, ide=ide, instance=instance)
