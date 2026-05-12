"""Tool registry + detection for AI coding tools (2026 roadmap phase 1)."""

from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path
from typing import Any

import yaml


def default_registry_path() -> Path:
    """Return the default in-repo registry path."""
    return Path(__file__).resolve().parents[2] / "docs" / "ai-tool-registry-2026.yaml"


def resolve_registry_path(path_override: Path | None = None) -> Path | None:
    """Resolve registry path from override/env/default in that order."""
    if path_override is not None:
        return path_override.resolve()
    env_path = os.getenv("KORU_TOOL_REGISTRY")
    if env_path:
        return Path(env_path).expanduser().resolve()
    candidate = default_registry_path()
    return candidate if candidate.is_file() else None


def load_tool_registry(path_override: Path | None = None) -> tuple[list[dict[str, Any]], Path | None]:
    """Load YAML registry and return ``(entries, path_used)``.

    Accepts either:
    - top-level list of tool dicts, or
    - ``{"tools": [ ... ]}``.
    """
    path = resolve_registry_path(path_override)
    if path is None or not path.is_file():
        return [], path
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return [], path

    tools: Any
    if isinstance(payload, list):
        tools = payload
    elif isinstance(payload, dict):
        tools = payload.get("tools")
    else:
        tools = None

    if not isinstance(tools, list):
        return [], path

    normalized: list[dict[str, Any]] = []
    for item in tools:
        if not isinstance(item, dict):
            continue
        tool_id = item.get("id")
        if not isinstance(tool_id, str) or not tool_id.strip():
            continue
        normalized.append(item)
    return normalized, path


def _first_token(command: str) -> str:
    parts = shlex.split(command)
    return parts[0] if parts else command


def detect_tools(project: Path, registry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect available tools from registry definitions."""
    project = project.resolve()
    out: list[dict[str, Any]] = []

    for item in registry:
        detect = item.get("detect") if isinstance(item.get("detect"), dict) else {}

        commands = [c for c in (detect.get("commands") or []) if isinstance(c, str)]
        markers = [m for m in (detect.get("markers") or []) if isinstance(m, str)]
        env_vars = [e for e in (detect.get("env") or []) if isinstance(e, str)]

        found_commands: list[str] = []
        for cmd in commands:
            token = _first_token(cmd)
            if shutil.which(token):
                found_commands.append(cmd)

        found_markers = [m for m in markers if (project / m).exists()]
        found_env = [e for e in env_vars if os.getenv(e)]

        available = bool(found_commands or found_markers or found_env)

        out.append(
            {
                "id": item.get("id"),
                "name": item.get("name") or item.get("id"),
                "category": item.get("category") or "unknown",
                "lane": item.get("lane") or "manual",
                "stability": item.get("stability") or "unknown",
                "available": available,
                "detected_via": {
                    "commands": found_commands,
                    "markers": found_markers,
                    "env": found_env,
                },
                "invoke": item.get("invoke") or "",
                "notes": item.get("notes") or "",
            }
        )

    return out


def render_tools_detect_text(results: list[dict[str, Any]], *, registry_path: Path | None) -> str:
    """Render a compact text report for ``koru tools detect``."""
    available = sum(1 for r in results if r.get("available"))
    lines = [
        "koru tools detect",
        f"registry: {registry_path if registry_path else '(not found)'}",
        f"summary: total={len(results)} available={available} missing={len(results)-available}",
        "",
        "| id | lane | category | available | via |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in results:
        via_parts: list[str] = []
        dv = r.get("detected_via") if isinstance(r.get("detected_via"), dict) else {}
        if dv.get("commands"):
            via_parts.append("cmd")
        if dv.get("markers"):
            via_parts.append("marker")
        if dv.get("env"):
            via_parts.append("env")
        via = ",".join(via_parts) if via_parts else "-"
        lines.append(
            f"| `{r.get('id')}` | `{r.get('lane')}` | `{r.get('category')}` | "
            f"`{r.get('available')}` | `{via}` |"
        )
    return "\n".join(lines)
