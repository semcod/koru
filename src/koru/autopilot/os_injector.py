"""Coordinate-based OS injector fallback for IDE chat input.

This backend is intentionally best-effort and X11/xdotool-focused.
Use it only as a fallback when plugin/MCP paths are unavailable.

Injection uses **only** stored mouse coordinates (``chat_x`` / ``chat_y``):
move the pointer there, focus the field (left click or Return), then paste
or type the prompt. Legacy ``window_id`` keys in JSON are ignored and no
longer written by :func:`save_profile`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class OsInjectorError(RuntimeError):
    """Raised when profile config or xdotool operations fail."""


@dataclass(frozen=True)
class OsInjectorProfile:
    """Chat anchor: pixel position under the cursor at calibration time."""

    tool_id: str
    chat_x: int
    chat_y: int
    window_id: int = 0  # legacy JSON only; never used for windowactivate


def default_config_path() -> Path:
    return Path.home() / ".koru" / "ide-os-injector.json"


def iter_config_paths(*, project: Path | None = None) -> list[Path]:
    """Search order: ``<project>/.koru/``, cwd ``.koru/``, then home."""
    raw: list[Path] = []
    if project is not None:
        raw.append(project.resolve() / ".koru" / "ide-os-injector.json")
    raw.append(Path.cwd() / ".koru" / "ide-os-injector.json")
    raw.append(Path.home() / ".koru" / "ide-os-injector.json")
    seen: set[str] = set()
    out: list[Path] = []
    for p in raw:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def os_injector_env_disabled() -> bool:
    raw = os.environ.get("KORU_OS_INJECTOR", "").strip().lower()
    return raw in ("0", "false", "no", "off")


def os_injector_env_forced() -> bool:
    raw = os.environ.get("KORU_OS_INJECTOR", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def dry_run_from_env() -> bool:
    raw = os.environ.get("KORU_OS_INJECTOR_DRY_RUN", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def focus_mode_from_env() -> str:
    """How to focus the chat field after moving the pointer.

    ``click`` (default): left-click at ``(chat_x, chat_y)``.
    ``return``: press Return at that position (no mouse click).
    """
    raw = os.environ.get("KORU_OS_INJECTOR_FOCUS", "click").strip().lower()
    if raw in ("return", "enter"):
        return "return"
    return "click"


def input_mode_from_env() -> str:
    """How to insert text: ``auto`` (paste if xclip/xsel else type), ``paste``, ``type``."""
    raw = os.environ.get("KORU_OS_INJECTOR_INPUT", "auto").strip().lower()
    if raw in ("paste", "type", "auto"):
        return raw
    return "auto"


def try_load_profile(tool_id: str, *, project: Path | None = None) -> OsInjectorProfile | None:
    """Load the first matching profile from :func:`iter_config_paths`."""
    for path in iter_config_paths(project=project):
        if not path.is_file():
            continue
        try:
            return load_profile(tool_id, config_path=path)
        except OsInjectorError:
            continue
    return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise OsInjectorError(f"invalid os-injector config: {path} ({exc})") from exc
    return data if isinstance(data, dict) else {}


def load_profile(tool_id: str, *, config_path: Path | None = None) -> OsInjectorProfile:
    path = (config_path or default_config_path()).resolve()
    data = _read_json(path)
    raw = data.get(tool_id)
    if not isinstance(raw, dict):
        raise OsInjectorError(f"missing profile {tool_id!r} in {path}")
    try:
        return OsInjectorProfile(
            tool_id=tool_id,
            chat_x=int(raw["chat_x"]),
            chat_y=int(raw["chat_y"]),
            window_id=int(raw.get("window_id") or 0),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise OsInjectorError(f"invalid profile {tool_id!r} in {path}: {exc}") from exc


def save_profile(profile: OsInjectorProfile, *, config_path: Path | None = None) -> Path:
    path = (config_path or default_config_path()).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path) if path.exists() else {}
    data[profile.tool_id] = {
        "chat_x": profile.chat_x,
        "chat_y": profile.chat_y,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def capture_mouse_xy() -> tuple[int, int]:
    """Return ``(x, y)`` from ``xdotool getmouselocation --shell``."""
    proc = subprocess.run(
        ["xdotool", "getmouselocation", "--shell"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise OsInjectorError(f"xdotool getmouselocation failed: {proc.stderr.strip()}")
    kv: dict[str, str] = {}
    for line in (proc.stdout or "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            kv[key.strip()] = value.strip()
    try:
        return int(kv["X"]), int(kv["Y"])
    except (KeyError, ValueError) as exc:
        raise OsInjectorError("xdotool output missing X/Y") from exc


def capture_from_xdotool() -> tuple[int, int, int]:
    """Return ``(0, x, y)`` — window id is unused; kept for older calibration scripts."""
    x, y = capture_mouse_xy()
    return 0, x, y


def _run_cmd(cmd: list[str], *, stdin: bytes | None = None) -> None:
    proc = subprocess.run(cmd, input=stdin, capture_output=True, text=False, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise OsInjectorError(f"{cmd[0]} failed ({proc.returncode}): {err or '(no stderr)'}")


def _xdotool(argv_tail: list[str]) -> None:
    _run_cmd(["xdotool", *argv_tail])


def _clipboard_backend() -> str | None:
    if shutil.which("xclip"):
        return "xclip"
    if shutil.which("xsel"):
        return "xsel"
    return None


def _set_clipboard(text: str) -> str:
    data = text.encode("utf-8")
    xclip = shutil.which("xclip")
    if xclip:
        _run_cmd([xclip, "-selection", "clipboard"], stdin=data)
        return "xclip"
    xsel = shutil.which("xsel")
    if xsel:
        _run_cmd([xsel, "--clipboard", "--input"], stdin=data)
        return "xsel"
    raise OsInjectorError("clipboard paste needs xclip or xsel on PATH")


def inject_with_profile(
    *,
    profile: OsInjectorProfile,
    text: str,
    submit: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not text.strip():
        raise OsInjectorError("refusing to inject empty text")

    focus = focus_mode_from_env()
    mode = input_mode_from_env()
    clip_ok = _clipboard_backend() is not None
    use_paste = mode == "paste" or (mode == "auto" and clip_ok)
    if mode == "paste" and not clip_ok:
        raise OsInjectorError("KORU_OS_INJECTOR_INPUT=paste requires xclip or xsel on PATH")
    input_method: str = "paste" if use_paste else "type"

    if dry_run:
        return {
            "ok": True,
            "backend": "os_injector",
            "tool_id": profile.tool_id,
            "submitted": submit,
            "dry_run": True,
            "chat_x": profile.chat_x,
            "chat_y": profile.chat_y,
            "focus": focus,
            "input_method": input_method,
        }

    x, y = profile.chat_x, profile.chat_y
    _xdotool(["mousemove", "--sync", str(x), str(y)])
    if focus == "click":
        _xdotool(["click", "1"])
    else:
        _xdotool(["key", "--clearmodifiers", "Return"])

    if use_paste:
        clip_tool = _set_clipboard(text)
        _xdotool(["sleep", "0.08"])
        _xdotool(["key", "--clearmodifiers", "ctrl+v"])
    else:
        _xdotool(["type", "--delay", "5", "--clearmodifiers", "--", text])

    if submit:
        _xdotool(["key", "--clearmodifiers", "Return"])

    return {
        "ok": True,
        "backend": "os_injector",
        "tool_id": profile.tool_id,
        "submitted": submit,
        "dry_run": False,
        "chat_x": profile.chat_x,
        "chat_y": profile.chat_y,
        "focus": focus,
        "input_method": input_method,
    }


def try_drive_with_profile(
    *,
    tool_id: str,
    text: str,
    submit: bool,
    project: Path | None,
    cli_dry_run: bool = False,
) -> dict[str, Any] | None:
    """If a profile applies, run :func:`inject_with_profile`; else return ``None``.

    Used by the autopilot daemon and ``koru autopilot drive --direct``.
    Requires ``xdotool`` on ``PATH`` (X11 or XWayland). Raises
    :class:`OsInjectorError` when injection is attempted but fails.
    """
    if tool_id == "default":
        return None
    if os_injector_env_disabled():
        return None
    if shutil.which("xdotool") is None:
        return None

    profile = try_load_profile(tool_id, project=project)
    if profile is None and not os_injector_env_forced():
        return None
    if profile is None:
        return None

    dry = cli_dry_run or dry_run_from_env()
    return inject_with_profile(profile=profile, text=text, submit=submit, dry_run=dry)
