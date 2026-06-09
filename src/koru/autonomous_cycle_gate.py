"""Cycle gating and lane-selection helpers for ``koru autonomous``."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from koru.agents import agent_lane_environment
from koru.autonomy.env import allow_gillm_autopilot_fallback, env_truthy
from koru.autonomous_startup import resolve_agent_lane_id
from koru.ide_router import resolve_ide_route
from koru.init import resolve_project_agent_lane
from gillm.injection.os_injector import OsInjectorError, inject_with_profile, load_profile


def nlp2uri_ide_control_enabled() -> bool:
    return env_truthy("KORU_IDE_CONTROL_VIA_NLP2URI", False)


def effective_ide_control_submit(*, submit: bool, ide: str) -> bool:
    """Resolve submit for IDE control drives.

    Cursor Glass composer with ``submit=true`` often runs ``focus_open`` and opens
    new panels/windows instead of pasting into the active chat. Default Cursor to
    paste-only unless the operator opts in with ``KORU_IDE_CONTROL_FORCE_SUBMIT=1``.
    """
    if env_truthy("KORU_IDE_CONTROL_PASTE_ONLY", False):
        return False
    if env_truthy("KORU_IDE_CONTROL_FORCE_SUBMIT", False):
        return submit
    from koruide.ide import canonical_autopilot_ide_id

    if canonical_autopilot_ide_id(ide) == "cursor":
        return False
    return submit


def _resolve_ide_chat_workspace(
    client: Any | None,
    *,
    ide: str,
    project: Path | None,
) -> str:
    project_path = str((project or Path.cwd()).expanduser().resolve())
    status_fn = getattr(client, "status", None)
    if not callable(status_fn):
        return project_path
    try:
        status = status_fn()
    except (OSError, TimeoutError, RuntimeError):
        return project_path
    plugins = status.get("plugins") if isinstance(status, dict) else None
    if not isinstance(plugins, list):
        return project_path
    from koruide.ide import canonical_autopilot_ide_id

    target = canonical_autopilot_ide_id(ide)
    for row in plugins:
        if not isinstance(row, dict):
            continue
        if canonical_autopilot_ide_id(str(row.get("ide") or "")) != target:
            continue
        folders = row.get("workspaceFolders")
        if not isinstance(folders, list) or not folders:
            continue
        for folder in folders:
            folder_s = str(folder).strip()
            if folder_s == project_path:
                return folder_s
        return str(folders[0]).strip()
    return project_path


def try_os_injector_fallback(prompt: str, *, submit: bool) -> dict[str, Any] | None:
    """Best-effort global fallback via coordinate profile.

    Enabled only when ``KORU_OS_INJECTOR_PROFILE`` is set.
    """
    profile_id = os.environ.get("KORU_OS_INJECTOR_PROFILE", "").strip()
    if not profile_id:
        return None
    raw_cfg = os.environ.get("KORU_OS_INJECTOR_CONFIG", "").strip()
    cfg = Path(raw_cfg).expanduser().resolve() if raw_cfg else None
    try:
        profile = load_profile(profile_id, config_path=cfg)
        return inject_with_profile(profile=profile, text=prompt, submit=submit, dry_run=False)
    except OsInjectorError as exc:
        return {"ok": False, "backend": "os_injector", "message": str(exc), "type": "error"}


def try_nlp2uri_ide_control(
    prompt: str,
    *,
    submit: bool,
    ide: str,
    client: Any = None,
    project: Path | None = None,
) -> dict[str, Any] | None:
    """IDE chat drive via nlp2uri control plan → koruide socket.

    Enabled when ``KORU_IDE_CONTROL_VIA_NLP2URI=1``.
    When *client* is provided, execution reuses that socket (same lane as autonomous).
    """
    if not nlp2uri_ide_control_enabled():
        return None
    try:
        from nlp2uri.control_execute import compile_and_execute_control_uri
        from nlp2uri.schemes.util import abstract_url
    except ImportError:
        return None

    effective_submit = effective_ide_control_submit(submit=submit, ide=ide)
    workspace = _resolve_ide_chat_workspace(client, ide=ide, project=project)
    params: dict[str, str] = {
        "submit": "true" if effective_submit else "false",
        "require_plugin": "false",
    }
    if workspace:
        params["workspace"] = workspace
    uri = abstract_url("ide-chat", ide, "/send", params=params)
    client_factory = (lambda: client) if client is not None else None
    result = compile_and_execute_control_uri(
        uri,
        text=prompt,
        dry_run=False,
        client_factory=client_factory,
    )
    exec_results = result.get("results") or []
    if not exec_results:
        return {"ok": False, "backend": "nlp2uri_control", "message": "no control results"}
    top = exec_results[0]
    reply = top.get("reply") if isinstance(top, dict) else {}
    return {
        "ok": bool(top.get("ok")),
        "backend": top.get("backend", "nlp2uri_control"),
        "message": top.get("error") or (reply or {}).get("message", ""),
        "type": "drive" if top.get("ok") else "error",
        "control_plan": result.get("plan"),
        "verification_status": top.get("verification_status"),
        "reply": reply,
        "submit": effective_submit,
        "workspace": workspace,
    }


def try_nlp2uri_focus_fallback(prompt: str, *, submit: bool, ide: str) -> dict[str, Any] | None:
    """Best-effort window-management fallback via nlp2uri desktop-window://focus.

    Enabled when ``KORU_NLP2URI_DESKTOP_FALLBACK=1`` is set.
    Uses proper window management (wmctrl/xdotool windowactivate) to focus the
    IDE window, then injects text via gillm Injector.
    """
    raw = os.environ.get("KORU_NLP2URI_DESKTOP_FALLBACK", "").strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return None
    from koru.agent_backend_runtime import _nlp2uri_desktop_send

    return _nlp2uri_desktop_send(prompt, ide=ide, submit=submit, dry_run=False)


def imgl_fallback_enabled() -> bool:
    from koru.integrations.imgl_client import imgl_fallback_enabled as _enabled

    return _enabled()


def try_imgl_gui_fallback(
    prompt: str,
    *,
    submit: bool,
    ide: str,
    project: Path | None = None,
) -> dict[str, Any] | None:
    """Best-effort vision-guided fallback via imgl (nlp2imgl / rest2imgl).

    Enabled when ``KORU_IMGL_FALLBACK=1``.
    """
    del project
    if not imgl_fallback_enabled():
        return None
    from koru.integrations.imgl_client import imgl_available, send_chat

    if not imgl_available():
        return None
    try:
        reply = send_chat(prompt, ide=ide, submit=submit)
        reply.setdefault("backend", "imgl")
        reply["fallback_from"] = "plugin"
        return reply
    except Exception as exc:
        return {
            "ok": False,
            "backend": "imgl",
            "message": str(exc),
            "type": "error",
            "fallback_from": "plugin",
        }


def try_gillm_gui_fallback(
    prompt: str,
    *,
    submit: bool,
    ide: str,
    project: Path | None = None,
    build_client_fn: Any = None,
) -> dict[str, Any] | None:
    """Best-effort Gillm GuiDriver fallback after plugin drive failure.

    Enabled when ``KORU_AUTOPILOT_GILLM_FALLBACK=1``.
    """
    if not allow_gillm_autopilot_fallback():
        return None
    from koru.ide_adapters.gillm_client import build_gillm_ide_client
    from koru.ide_adapters.gillm_recovery import enrich_drive_reply_with_recovery

    build_fn = build_client_fn or build_gillm_ide_client
    dry_run = os.environ.get("KORU_OS_INJECTOR_DRY_RUN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    try:
        client = build_fn(project=project, dry_run=dry_run)
        reply = client.drive(prompt, submit=submit, ide=ide)
        reply.setdefault("backend", "gillm")
        reply["fallback_from"] = "plugin"
        if not reply.get("ok"):
            enrich_drive_reply_with_recovery(reply)
        return reply
    except Exception as exc:
        return {
            "ok": False,
            "backend": "gillm",
            "message": str(exc),
            "type": "error",
            "fallback_from": "plugin",
        }


def try_os_injector_fallback_with_deps(
    prompt: str,
    *,
    submit: bool,
    load_profile_fn: Any,
    inject_with_profile_fn: Any,
    os_injector_error: type[Exception],
) -> dict[str, Any] | None:
    """Best-effort OS injector fallback with injectable callables for tests."""
    profile_id = os.environ.get("KORU_OS_INJECTOR_PROFILE", "").strip()
    if not profile_id:
        return None
    raw_cfg = os.environ.get("KORU_OS_INJECTOR_CONFIG", "").strip()
    cfg = Path(raw_cfg).expanduser().resolve() if raw_cfg else None
    try:
        profile = load_profile_fn(profile_id, config_path=cfg)
        return inject_with_profile_fn(profile=profile, text=prompt, submit=submit, dry_run=False)
    except os_injector_error as exc:
        return {"ok": False, "backend": "os_injector", "message": str(exc), "type": "error"}


def allow_keyboard_autopilot_fallback() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def effective_cycle_autopilot_enabled(
    enabled: bool,
    *,
    client: object | None,
    autopilot_ide: str,
    stdio_format: str,
    plugin_required_for_ide: Any,
    status_has_autopilot_plugin: Any,
    stdio_info: Any,
) -> bool:
    if not enabled:
        return False
    if not plugin_required_for_ide(autopilot_ide):
        return True
    plugin_ready = False
    if client is not None:
        status_fn = getattr(client, "status", None)
        if callable(status_fn):
            for attempt in range(2):
                try:
                    plugin_ready = status_has_autopilot_plugin(status_fn(), autopilot_ide)
                except OSError:
                    plugin_ready = False
                if plugin_ready or attempt == 1:
                    break
                time.sleep(0.25)
    if plugin_ready:
        return True
    stdio_info(
        "koru autonomous: autopilot skipped this cycle; "
        f"ide={autopilot_ide} requires a compatible connected plugin",
        fmt=stdio_format,
    )
    return False


def scan_while_waiting_input_enabled() -> bool:
    raw = os.environ.get("KORU_AUTONOMOUS_SCAN_WHILE_WAITING", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def effective_cycle_scan_enabled(
    enabled: bool,
    *,
    state: object,
    stdio_format: str,
    stdio_info: Any,
) -> bool:
    if not enabled:
        return False
    if scan_while_waiting_input_enabled():
        return True
    signature = str(getattr(state, "previous_signature", "") or "")
    if signature.startswith("waiting_input:"):
        waiting_ticket = signature.split(":", 1)[1] or "-"
        stdio_info(
            "koru autonomous: scan skipped this cycle; "
            f"queue is waiting_input ({waiting_ticket})",
            fmt=stdio_format,
        )
        return False
    return True


def resolve_autopilot_ide(cli_value: str) -> str:
    """Resolve autopilot ``--ide`` via :mod:`koru.ide_router`."""
    return resolve_ide_route(cli_autopilot_ide=cli_value).autopilot_ide


def apply_agent_lane_environ(project: Path, agent_lane: str) -> str | None:
    """Set lane exports in ``os.environ``; returns lane id or ``None`` if skipped."""
    lane, _source = resolve_agent_lane_id(
        project,
        agent_lane,
        resolve_project_lane=resolve_project_agent_lane,
    )
    if lane is None:
        return None
    for key, val in agent_lane_environment(lane).items():
        os.environ[key] = val
    return lane


__all__ = [
    "effective_ide_control_submit",
    "nlp2uri_ide_control_enabled",
    "allow_keyboard_autopilot_fallback",
    "apply_agent_lane_environ",
    "effective_cycle_autopilot_enabled",
    "effective_cycle_scan_enabled",
    "resolve_autopilot_ide",
    "scan_while_waiting_input_enabled",
    "imgl_fallback_enabled",
    "try_gillm_gui_fallback",
    "try_imgl_gui_fallback",
    "try_nlp2uri_ide_control",
    "try_nlp2uri_focus_fallback",
    "try_os_injector_fallback",
    "try_os_injector_fallback_with_deps",
]
