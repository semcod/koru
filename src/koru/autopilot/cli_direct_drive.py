"""Direct-drive fallback subsystem for ``koru autopilot drive``.

Extracted from :mod:`koru.autopilot.cli_command` (R5 — FAZA 2) to isolate the
OS-injector + keyboard-injector fallback pipeline from the rest of the CLI
dispatcher. All functions remain ``_`` private; ``koru.autopilot.cli_command``
re-exports them so legacy imports (and test monkeypatches targeting
``cli_command._run_direct_drive``) keep working unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

from gillm.injection.errors import InjectorError
from gillm.injection.injector import Injector
from koru.control_commands import desktop_gui_command


def _auto_direct_fallback_enabled() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", "").strip().lower()
    if not raw:
        return True
    return raw not in {"0", "false", "no", "off"}


def _should_fallback_to_direct(args: argparse.Namespace, reply: dict[str, Any]) -> bool:
    if args.require_plugin:
        return False
    if not _auto_direct_fallback_enabled():
        return False
    if bool(reply.get("ok", True)):
        return False
    message = str(reply.get("message") or "").lower()
    if "chat input is not focused/open" in message:
        return True
    return bool(reply.get("opened") is False and reply.get("submitted") is False)


def _print_drive_delay_message(delay_seconds: float) -> None:
    """Print delay message before direct injection."""
    print(
        f"koru autopilot drive: waiting {delay_seconds:.1f}s "
        "before direct injection (focus the target IDE now)...",
        file=sys.stderr,
    )
    time.sleep(delay_seconds)


def _handle_os_injector_fallback(
    args: argparse.Namespace, profile_id: str, injector: Injector
) -> tuple[int, dict[str, Any] | None]:
    """Handle fallback when OS injector is unavailable."""
    if args.os_profile:
        print(
            "koru autopilot drive: requested --os-profile but os-injector path is unavailable. "
            "Run `koru autopilot calibrate --ide <id>` first, or install xdotool.",
            file=sys.stderr,
        )
        return 2, None
    if injector.session == "wayland":
        print(
            "koru autopilot drive: no OS-injector profile for "
            f"{profile_id!r}; using ydotool/wtype (keystrokes go only to the "
            "currently focused window — click the IDE chat first, or run "
            "`koru autopilot calibrate --ide auto`).",
            file=sys.stderr,
        )
    return None, None


def _emit_direct_drive_auto_selection(
    args: argparse.Namespace,
    profile_id: str,
    selection: str,
) -> None:
    raw_ide = (args.ide or "").strip().lower()
    if raw_ide in ("", "auto") and not (args.os_profile or "").strip():
        print(
            f"koru autopilot drive: auto-selected {profile_id} ({selection})",
            file=sys.stderr,
        )


def _emit_json_payload(payload: dict[str, Any], *, enabled: bool) -> None:
    if enabled:
        print(json.dumps(payload, indent=2, sort_keys=True))


def _direct_drive_corr() -> str:
    return f"direct-drive-{time.monotonic_ns():x}"


def _emit_desktop_drive_command(
    args: argparse.Namespace,
    *,
    corr: str,
    operation: str,
    backend: str,
    target: str,
    text: str,
    replayable: bool,
    **payload: Any,
) -> None:
    project = getattr(args, "project", None)
    desktop_gui_command(
        project,
        corr=corr,
        operation=operation,
        backend=backend,
        target=target,
        payload={
            "text": text,
            "text_len": len(text),
            "submit": bool(getattr(args, "submit", True)),
            "dry_run": bool(getattr(args, "dry_run", False)),
            **payload,
        },
        actor="koru-autopilot-cli",
        replayable=replayable,
    )


def _try_profile_direct_drive(
    args: argparse.Namespace,
    text: str,
    profile_id: str,
    *,
    corr: str,
    emit_payload: bool,
) -> tuple[bool, int, dict[str, Any] | None]:
    import gillm.injection.os_injector as oi

    if float(args.delay_seconds) > 0:
        _print_drive_delay_message(float(args.delay_seconds))
    _emit_desktop_drive_command(
        args,
        corr=corr,
        operation="os_injector.profile_drive",
        backend="os_injector",
        target=profile_id,
        text=text,
        profile_id=profile_id,
        replayable=True,
    )
    os_res = oi.try_drive_with_profile(
        tool_id=profile_id,
        text=text,
        submit=args.submit,
        project=args.project,
        cli_dry_run=args.dry_run,
    )
    if os_res is None:
        return False, 0, None
    _emit_json_payload(os_res, enabled=emit_payload)
    return True, 0, os_res


def _selected_keyboard_backend(injector: Injector) -> str:
    select_backend = getattr(injector, "select_backend", None)
    selected = select_backend() if callable(select_backend) else getattr(injector, "session", "")
    return str(selected or "keyboard")


def _type_text_direct_drive(
    args: argparse.Namespace,
    text: str,
    *,
    corr: str,
    target_id: str,
    injector: Injector,
    emit_payload: bool,
) -> tuple[int, dict[str, Any] | None]:
    _emit_desktop_drive_command(
        args,
        corr=corr,
        operation="injector.type_text",
        backend=_selected_keyboard_backend(injector),
        target=target_id,
        text=text,
        ide=target_id,
        replayable=False,
    )
    result = injector.type_text(
        text,
        ide=target_id,
        submit=args.submit,
        dry_run=args.dry_run,
    )
    payload = result.to_dict()
    _emit_json_payload(payload, enabled=emit_payload)
    return 0, payload


def _handle_os_profile_direct_error(
    args: argparse.Namespace,
    profile_id: str,
    exc: Exception,
) -> bool:
    if not args.os_profile:
        return False
    print(
        f"koru autopilot drive: os-injector failed for requested profile "
        f"{profile_id!r}: {exc}",
        file=sys.stderr,
    )
    return True


def _run_direct_drive(
    args: argparse.Namespace,
    text: str,
    *,
    emit_payload: bool = True,
) -> tuple[int, dict[str, Any] | None]:
    # Resolve ``Injector`` and ``resolve_drive_target`` via the
    # ``cli_command`` module so that existing tests which monkeypatch
    # ``cli_command.Injector`` / ``cli_command.resolve_drive_target``
    # keep affecting this code path after the R5 extraction.
    from koru.autopilot import cli_command
    import gillm.injection.os_injector as oi

    injector = cli_command.Injector()
    target_id, profile_id, selection = cli_command.resolve_drive_target(
        args.ide,
        args.os_profile,
        project=args.project,
    )
    corr = _direct_drive_corr()
    _emit_direct_drive_auto_selection(args, profile_id, selection)

    try:
        handled, rc, payload = _try_profile_direct_drive(
            args,
            text,
            profile_id,
            corr=corr,
            emit_payload=emit_payload,
        )
        if handled:
            return rc, payload
        fallback_rc, _unused_payload = _handle_os_injector_fallback(args, profile_id, injector)
        if fallback_rc is not None:
            return fallback_rc, None
        return _type_text_direct_drive(
            args,
            text,
            corr=corr,
            target_id=target_id,
            injector=injector,
            emit_payload=emit_payload,
        )
    except oi.OsInjectorError as exc:
        if _handle_os_profile_direct_error(args, profile_id, exc):
            return 1, None
        print(
            f"koru autopilot drive: os-injector failed; falling back to keyboard injector: {exc}",
            file=sys.stderr,
        )
        try:
            return _type_text_direct_drive(
                args,
                text,
                corr=corr,
                target_id=target_id,
                injector=injector,
                emit_payload=emit_payload,
            )
        except InjectorError as inner_exc:
            print(f"koru autopilot drive: {inner_exc}", file=sys.stderr)
            return 1, None
    except InjectorError as exc:
        print(f"koru autopilot drive: {exc}", file=sys.stderr)
        return 1, None
