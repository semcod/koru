"""Domain definitions and low-level parsers for Koru environment configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.dotenv_loader import parse_dotenv

ENV_FILENAME = ".env"


@dataclass(frozen=True)
class EnvKey:
    name: str
    default: str
    description: str
    group: str = "vision"


KORU_ENV_KEYS: tuple[EnvKey, ...] = (
    EnvKey(
        "KORU_VISION_INTERVAL",
        "30",
        "Seconds between captures (minimum 30 — see KORU_VISION_INTERVAL_MIN).",
        "vision",
    ),
    EnvKey(
        "KORU_VISION_INTERVAL_MIN",
        "30",
        "Hard floor for capture interval. Lower values are clamped up automatically.",
        "vision",
    ),
    EnvKey(
        "KORU_VISION_PROVIDER",
        "auto",
        "Capture provider: auto | obs_websocket | portal_screencast | "
        "mss | portal | grim | cli_tools.",
        "vision",
    ),
    EnvKey(
        "KORU_OBS_URL",
        "ws://127.0.0.1:4455",
        "OBS WebSocket URL (obs-websocket v5, built into OBS 28+).",
        "vision",
    ),
    EnvKey(
        "KORU_OBS_PASSWORD",
        "",
        "OBS WebSocket password (empty when authentication is disabled).",
        "vision",
    ),
    EnvKey(
        "KORU_OBS_SOURCE",
        "Display Capture",
        "OBS source name for GetSourceScreenshot (scene item / display capture).",
        "vision",
    ),
    EnvKey(
        "KORU_OBS_IMAGE_WIDTH",
        "1920",
        "Max width passed to OBS GetSourceScreenshot (height scales automatically).",
        "vision",
    ),
    EnvKey(
        "KORU_VISION_BROWSER",
        "false",
        "When true, rank browser_getdisplay (upload via /capture/host) in auto provider order.",
        "vision",
    ),
    EnvKey(
        "KORU_VISION_BROWSER_INTERVAL",
        "",
        "Seconds between browser uploads (defaults to KORU_VISION_INTERVAL, minimum 5).",
        "vision",
    ),
    EnvKey(
        "KORU_VISION_BACKEND",
        "auto",
        "Legacy alias for KORU_VISION_PROVIDER (auto | mss | portal | command).",
        "vision",
    ),
    EnvKey(
        "KORU_VISION_SCALE",
        "0.2",
        "Thumbnail scale relative to native resolution (0.05 – 1.0).",
        "vision",
    ),
    EnvKey(
        "KORU_VISION_PREFER_PORTAL",
        "false",
        "When true on Wayland, try the portal screenshot before mss.",
        "vision",
    ),
    EnvKey(
        "KORU_PORTAL_PYTHON",
        "",
        "Python interpreter used for the D-Bus portal subprocess (auto-detected when empty).",
        "vision",
    ),
    EnvKey(
        "KORU_OBSERVE_PYTHON",
        "",
        "Python interpreter used by koru observe child processes (auto-detected when empty).",
        "observe",
    ),
    EnvKey(
        "KORU_MESH_FRAME_STORE",
        "",
        "JSONL file used to persist mesh frames (default: .koru/run/mesh-frames.jsonl).",
        "observe",
    ),
    EnvKey(
        "KORU_AGENT_LANE",
        "",
        "Override agent lane identifier (defaults to host / IDE detection).",
        "runtime",
    ),
    EnvKey(
        "KORU_PLANFILE_CMD",
        "",
        "Override the planfile CLI executable (empty = use PATH lookup).",
        "runtime",
    ),
)


def env_path(project: Path) -> Path:
    return project.resolve() / ENV_FILENAME


def _format_env_value(value: str) -> str:
    if value == "":
        return ""
    if any(ch.isspace() for ch in value) or "#" in value:
        return '"' + value.replace('"', '\\"') + '"'
    return value


def _build_env_payload(project: Path, environ: dict[str, str]) -> dict[str, Any]:
    """Return current ``.env`` + environment snapshot for known koru keys."""
    path = env_path(project)
    file_values: dict[str, str] = {}
    if path.is_file():
        try:
            file_values = parse_dotenv(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            file_values = {}
    keys: list[dict[str, Any]] = []
    for spec in KORU_ENV_KEYS:
        keys.append(
            {
                "name": spec.name,
                "group": spec.group,
                "default": spec.default,
                "description": spec.description,
                "file_value": file_values.get(spec.name, ""),
                "env_value": environ.get(spec.name, ""),
                "in_file": spec.name in file_values,
            }
        )
    return {
        "ok": True,
        "path": str(path),
        "exists": path.is_file(),
        "keys": keys,
    }


def _env_assignment_key(raw: str) -> str | None:
    stripped = raw.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key_part = stripped.split("=", 1)[0].strip()
    if key_part.startswith("export "):
        key_part = key_part[len("export ") :].strip()
    return key_part


def _merge_existing_env_lines(
    lines: list[str],
    updates: dict[str, str],
) -> tuple[list[str], set[str]]:
    seen: set[str] = set()
    output: list[str] = []
    for raw in lines:
        key_part = _env_assignment_key(raw)
        if key_part is None:
            output.append(raw)
            continue
        if key_part in updates:
            new_value = _format_env_value(updates[key_part])
            output.append(f"{key_part}={new_value}")
            seen.add(key_part)
        else:
            output.append(raw)
    return output, seen


def _append_missing_env_updates(
    output: list[str],
    updates: dict[str, str],
    seen: set[str],
) -> None:
    appended_header = False
    for key in updates:
        if key in seen:
            continue
        if not appended_header:
            if output and output[-1].strip():
                output.append("")
            output.append("# Added by koru dashboard")
            appended_header = True
        output.append(f"{key}={_format_env_value(updates[key])}")


def _write_env_file(project: Path, updates: dict[str, str]) -> Path:
    """Merge ``updates`` into ``<project>/.env`` preserving comments and order."""
    path = env_path(project)
    existing_text = ""
    if path.is_file():
        try:
            existing_text = path.read_text(encoding="utf-8")
        except OSError:
            existing_text = ""
    lines = existing_text.splitlines() if existing_text else []
    output, seen = _merge_existing_env_lines(lines, updates)
    _append_missing_env_updates(output, updates, seen)
    payload = "\n".join(output)
    if not payload.endswith("\n"):
        payload += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path
