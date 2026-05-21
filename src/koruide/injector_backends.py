"""Concrete keyboard injector backend commands."""

from __future__ import annotations

import os
from collections.abc import Callable

from koruide.injector_errors import InjectorError

RunnerCall = Callable[[list[str]], None]
LogFn = Callable[[str], None] | None


def ydotool_enter_keycode() -> str:
    """Keycode used by ydotool for submit."""
    raw = os.environ.get("KORU_YDOTOOL_ENTER_KEYCODE", "").strip()
    if raw.isdigit():
        return raw
    return "28"


def ydotool_submit_mode() -> str:
    """How to submit for ydotool: ``keycode`` (default), ``newline``, ``ctrl-enter``."""
    raw = os.environ.get("KORU_YDOTOOL_SUBMIT_MODE", "").strip().lower()
    if raw in ("newline", "nl", "linefeed"):
        return "newline"
    if raw in ("ctrl-enter", "ctrl_enter", "ctrl+enter"):
        return "ctrl-enter"
    return "keycode"


def ydotool_ctrl_keycode() -> str:
    """Keycode used for Ctrl in ydotool chord submit mode."""
    raw = os.environ.get("KORU_YDOTOOL_CTRL_KEYCODE", "").strip()
    if raw.isdigit():
        return raw
    return "29"


def extra_enter_count() -> int:
    """Optional extra submit presses after normal submit."""
    raw = os.environ.get("KORU_INJECTOR_EXTRA_ENTER", "").strip()
    if not raw:
        return 0
    try:
        value = int(raw)
    except ValueError:
        return 0
    return max(0, value)


def _log(log: LogFn, message: str) -> None:
    if log:
        log(message)


def type_with_xdotool(
    call: RunnerCall,
    log: LogFn,
    text: str,
    submit_key: str | None,
    extra_enters: int,
) -> None:
    """Type text using xdotool backend."""
    _log(log, f"injector: xdotool typing {len(text)} chars, submit={submit_key}, extra_enters={extra_enters}")
    call(["xdotool", "type", "--delay", "5", "--clearmodifiers", "--", text])
    if not submit_key:
        return
    _log(log, f"injector: xdotool pressing submit key {submit_key}")
    call(["xdotool", "key", "--clearmodifiers", submit_key])
    for i in range(extra_enters):
        _log(log, f"injector: xdotool extra Enter #{i+1}")
        call(["xdotool", "key", "--clearmodifiers", "Return"])


def press_wtype(call: RunnerCall, combo: str) -> None:
    """Press a wtype key combo with at most one modifier."""
    parts = combo.split("+")
    key = parts[-1]
    modifiers = parts[:-1]
    if len(modifiers) > 1:
        raise InjectorError(
            f"wtype submit key {combo!r} has {len(modifiers)} modifiers; "
            "only single-modifier combos are supported",
        )
    argv = ["wtype"]
    for modifier in modifiers:
        argv += ["-M", modifier]
    argv += ["-k", key]
    for modifier in reversed(modifiers):
        argv += ["-m", modifier]
    call(argv)


def type_with_wtype(
    call: RunnerCall,
    log: LogFn,
    text: str,
    submit_key: str | None,
    extra_enters: int,
) -> None:
    """Type text using wtype backend."""
    _log(log, f"injector: wtype typing {len(text)} chars, submit={submit_key}, extra_enters={extra_enters}")
    call(["wtype", "--", text])
    if not submit_key:
        return
    _log(log, f"injector: wtype pressing submit key {submit_key}")
    press_wtype(call, submit_key)
    for i in range(extra_enters):
        _log(log, f"injector: wtype extra Enter #{i+1}")
        call(["wtype", "-k", "Return"])


def _ydotool_submit_command(
    submit_mode: str,
    enter_code: str,
    ctrl_code: str,
) -> list[str]:
    if submit_mode == "newline":
        return ["ydotool", "type", "--", "\n"]
    if submit_mode == "ctrl-enter":
        return [
            "ydotool",
            "key",
            f"{ctrl_code}:1",
            f"{enter_code}:1",
            f"{enter_code}:0",
            f"{ctrl_code}:0",
        ]
    return ["ydotool", "key", f"{enter_code}:1", f"{enter_code}:0"]


def type_with_ydotool(
    call: RunnerCall,
    log: LogFn,
    text: str,
    submit_key: str | None,
    extra_enters: int,
    enter_code: str,
    submit_mode: str,
    ctrl_code: str,
) -> None:
    """Type text using ydotool backend."""
    _log(
        log,
        f"injector: ydotool typing {len(text)} chars, submit={submit_key}, "
        f"mode={submit_mode}, enter_code={enter_code}, extra_enters={extra_enters}",
    )
    call(["ydotool", "type", "--", text])
    if not submit_key:
        return
    if submit_mode == "newline":
        _log(log, "injector: ydotool submitting via newline")
    elif submit_mode == "ctrl-enter":
        _log(log, f"injector: ydotool submitting via ctrl-enter (ctrl_code={ctrl_code}, enter_code={enter_code})")
    else:
        _log(log, f"injector: ydotool submitting via keycode {enter_code}")
    call(_ydotool_submit_command(submit_mode, enter_code, ctrl_code))
    for i in range(extra_enters):
        _log(log, f"injector: ydotool extra submit #{i+1} (mode={submit_mode})")
        call(_ydotool_submit_command(submit_mode, enter_code, ctrl_code))


def type_with_backend(
    call: RunnerCall,
    log: LogFn,
    backend: str,
    text: str,
    submit_key: str | None,
) -> None:
    """Dispatch a text injection request to a concrete backend."""
    _log(
        log,
        f"injector: typing {len(text)} chars via {backend} "
        f"(submit_key={submit_key or 'none'})",
    )
    extra_enters = extra_enter_count()
    if backend == "xdotool":
        type_with_xdotool(call, log, text, submit_key, extra_enters)
    elif backend == "wtype":
        type_with_wtype(call, log, text, submit_key, extra_enters)
    elif backend == "ydotool":
        type_with_ydotool(
            call,
            log,
            text,
            submit_key,
            extra_enters,
            ydotool_enter_keycode(),
            ydotool_submit_mode(),
            ydotool_ctrl_keycode(),
        )
    else:
        raise InjectorError(f"unreachable: unknown backend {backend!r}")


__all__ = [
    "extra_enter_count",
    "press_wtype",
    "type_with_backend",
    "type_with_wtype",
    "type_with_xdotool",
    "type_with_ydotool",
    "ydotool_ctrl_keycode",
    "ydotool_enter_keycode",
    "ydotool_submit_mode",
]
