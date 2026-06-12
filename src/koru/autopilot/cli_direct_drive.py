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


def _drive_verify_enabled(args: argparse.Namespace) -> bool:
    if bool(getattr(args, "verify", False)):
        return True
    raw = os.environ.get("KORU_DRIVE_VERIFY", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _record_direct_drive_audit(
    payload: dict[str, Any] | None,
    *,
    profile_id: str,
    text: str,
) -> None:
    if not payload:
        return
    try:
        from koru.integrations.vdisplay_client import record_koru_drive_step

        record_koru_drive_step(payload, profile_id=profile_id, text=text)
    except Exception:
        pass


def _resolve_verify_coords(
    payload: dict[str, Any],
) -> tuple["int | None", "int | None"]:
    """Extract (chat_x, chat_y) from payload, falling back to typed target coords."""
    chat_x = payload.get("chat_x")
    chat_y = payload.get("chat_y")
    if chat_x is not None:
        return chat_x, chat_y
    typed = payload.get("typed") if isinstance(payload.get("typed"), dict) else {}
    map_path = payload.get("map_path")
    target = typed.get("target") if isinstance(typed.get("target"), dict) else {}
    state = target.get("state") if isinstance(target.get("state"), dict) else {}
    click = state.get("click_point") if isinstance(state.get("click_point"), dict) else {}
    if click.get("x") is not None and map_path:
        try:
            from vdisplay.control.gui_map import load_gui_map
            from vdisplay.input.coords import global_pointer_coords

            pack = load_gui_map(str(map_path))
            element = pack.elements.get(str(typed.get("map_target") or "ai-chat-input"))
            meta = (element.capture_meta if element else None) or pack.capture_meta or {}
            chat_x, chat_y, _ = global_pointer_coords(int(click["x"]), int(click["y"]), meta)
        except Exception:
            pass
    return chat_x, chat_y


def _apply_drive_verification(
    args: argparse.Namespace,
    payload: dict[str, Any] | None,
    *,
    text: str,
    profile_id: str,
) -> tuple[dict[str, Any] | None, int]:
    if payload is None or not payload.get("ok") or not _drive_verify_enabled(args):
        return payload, 0
    from koru.integrations.vdisplay_client import verify_chat_text_visible

    map_path = payload.get("map_path")
    chat_x, chat_y = _resolve_verify_coords(payload)
    verification = verify_chat_text_visible(
        text,
        ide=profile_id,
        chat_x=int(chat_x) if chat_x is not None else None,
        chat_y=int(chat_y) if chat_y is not None else None,
        map_path=str(map_path) if map_path else None,
    )
    payload["verification"] = verification
    payload["verified"] = verification.get("verified")
    payload["verify_mode"] = verification.get("mode")
    if verification.get("screenshot_path"):
        payload.setdefault("artifacts", {})["verify_screenshot"] = verification["screenshot_path"]
    if verification.get("verified") is False:
        payload["ok"] = False
        payload["message"] = str(
            verification.get("error") or verification.get("reason") or "chat text verify failed"
        )
        return payload, 1
    return payload, 0


def _should_fallback_to_direct(args: argparse.Namespace, reply: dict[str, Any]) -> bool:
    from koru.autopilot.drive_repair_policy import daemon_reply_blocks_direct_fallback

    if args.require_plugin:
        return False
    if not _auto_direct_fallback_enabled():
        return False
    if daemon_reply_blocks_direct_fallback(reply):
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


def _prefer_calibrated_os_injector(profile_id: str, project: Any) -> bool:
    """Use mouse calibration when available for JetBrains/PyCharm on Wayland."""
    if profile_id not in {"jetbrains", "pycharm"}:
        return False
    from pathlib import Path

    import gillm.injection.os_injector as oi

    project_path = Path(project) if project else None
    return oi.try_load_profile(profile_id, project=project_path) is not None


def _try_vdisplay_ide_prompt_direct(
    args: argparse.Namespace,
    text: str,
    profile_id: str,
    *,
    corr: str,
    emit_payload: bool,
) -> tuple[bool, int, dict[str, Any] | None]:
    if profile_id not in {"jetbrains", "pycharm"}:
        return False, 0, None
    from koru.integrations.vdisplay_client import send_chat_via_ide_prompt, vdisplay_available

    if not vdisplay_available():
        return False, 0, None
    if float(args.delay_seconds) > 0:
        _print_drive_delay_message(float(args.delay_seconds))
    _emit_desktop_drive_command(
        args,
        corr=corr,
        operation="vdisplay.ide_prompt",
        backend="vdisplay+ide-prompt",
        target=profile_id,
        text=text,
        replayable=True,
    )
    result = send_chat_via_ide_prompt(
        text,
        ide=profile_id,
        submit=args.submit,
        dry_run=args.dry_run,
        verify=_drive_verify_enabled(args),
    )
    if result is None or not result.get("ok"):
        return False, 0, result
    verify_rc = 0
    if _drive_verify_enabled(args):
        typed_block = result.get("typed") if isinstance(result.get("typed"), dict) else {}
        if typed_block.get("verified") is None:
            result, verify_rc = _apply_drive_verification(args, result, text=text, profile_id=profile_id)
        else:
            result["verified"] = typed_block.get("verified")
            if not typed_block.get("verified"):
                result["ok"] = False
                verify_rc = 1
    _emit_json_payload(result, enabled=emit_payload)
    _record_direct_drive_audit(result, profile_id=profile_id, text=text)
    return True, verify_rc, result


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
    verify_rc = 0
    if _drive_verify_enabled(args):
        os_res, verify_rc = _apply_drive_verification(args, os_res, text=text, profile_id=profile_id)
    _emit_json_payload(os_res, enabled=emit_payload)
    _record_direct_drive_audit(os_res, profile_id=profile_id, text=text)
    return True, verify_rc if os_res.get("ok") else 1, os_res


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
        profile_first = _prefer_calibrated_os_injector(profile_id, args.project)
        drive_attempts: tuple[str, ...] = (
            ("profile", "vdisplay") if profile_first else ("vdisplay", "profile")
        )
        for attempt in drive_attempts:
            if attempt == "vdisplay":
                handled, rc, payload = _try_vdisplay_ide_prompt_direct(
                    args,
                    text,
                    profile_id,
                    corr=corr,
                    emit_payload=emit_payload,
                )
            else:
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
