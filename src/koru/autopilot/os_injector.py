"""Coordinate-based OS injector fallback for IDE chat input.

This backend is intentionally best-effort and X11/xdotool-focused.
Use it only as a fallback when plugin/MCP paths are unavailable.
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
    tool_id: str
    window_id: int
    chat_x: int
    chat_y: int


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
            window_id=int(raw["window_id"]),
            chat_x=int(raw["chat_x"]),
            chat_y=int(raw["chat_y"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise OsInjectorError(f"invalid profile {tool_id!r} in {path}: {exc}") from exc


def save_profile(profile: OsInjectorProfile, *, config_path: Path | None = None) -> Path:
    path = (config_path or default_config_path()).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path) if path.exists() else {}
    data[profile.tool_id] = {
        "window_id": profile.window_id,
        "chat_x": profile.chat_x,
        "chat_y": profile.chat_y,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def capture_from_xdotool() -> tuple[int, int, int]:
    """Return ``(window_id, x, y)`` from xdotool.

    ``window_id`` is taken from ``getactivewindow`` (more reliable for IDE
    top-level focus) with fallback to ``getmouselocation --shell`` WINDOW.
    """
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
    active_id: int | None = None
    proc_active = subprocess.run(
        ["xdotool", "getactivewindow"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc_active.returncode == 0:
        raw = (proc_active.stdout or "").strip()
        if raw.isdigit():
            active_id = int(raw)
    try:
        fallback_window = int(kv["WINDOW"])
        return (active_id or fallback_window), int(kv["X"]), int(kv["Y"])
    except (KeyError, ValueError) as exc:
        raise OsInjectorError("xdotool output missing WINDOW/X/Y") from exc


def inject_with_profile(
    *,
    profile: OsInjectorProfile,
    text: str,
    submit: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not text.strip():
        raise OsInjectorError("refusing to inject empty text")
    if dry_run:
        return {
            "ok": True,
            "backend": "os_injector",
            "tool_id": profile.tool_id,
            "submitted": submit,
            "dry_run": True,
            "window_id": profile.window_id,
            "chat_x": profile.chat_x,
            "chat_y": profile.chat_y,
        }

    commands: list[list[str]] = [
        ["xdotool", "windowactivate", "--sync", str(profile.window_id)],
        ["xdotool", "mousemove", str(profile.chat_x), str(profile.chat_y), "click", "1"],
        ["xdotool", "type", "--delay", "5", "--clearmodifiers", "--", text],
    ]
    if submit:
        commands.append(["xdotool", "key", "--clearmodifiers", "Return"])

    for cmd in commands:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise OsInjectorError(f"{cmd[0]} failed ({proc.returncode}): {proc.stderr.strip()}")
    return {
        "ok": True,
        "backend": "os_injector",
        "tool_id": profile.tool_id,
        "submitted": submit,
        "dry_run": False,
        "window_id": profile.window_id,
        "chat_x": profile.chat_x,
        "chat_y": profile.chat_y,
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
