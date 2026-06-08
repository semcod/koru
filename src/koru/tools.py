"""Tool registry + detection for AI coding tools (2026 roadmap phase 1)."""

from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path
from typing import Any

import yaml

from koru.tillm_bridge import shell_tool_registry_entries


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


def load_tool_registry(
    path_override: Path | None = None,
) -> tuple[list[dict[str, Any]], Path | None]:
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
    if path_override is None and not os.getenv("KORU_TOOL_REGISTRY"):
        seen = {str(item.get("id") or "").strip().lower() for item in normalized}
        for item in shell_tool_registry_entries():
            tool_id = str(item.get("id") or "").strip().lower()
            if tool_id and tool_id not in seen:
                normalized.append(dict(item))
                seen.add(tool_id)
    return normalized, path


def _first_token(command: str) -> str:
    parts = shlex.split(command)
    return parts[0] if parts else command


def _extract_detect_config(item: dict[str, Any]) -> dict[str, list[str]]:
    """Extract detection configuration from a registry item."""
    detect = item.get("detect") if isinstance(item.get("detect"), dict) else {}
    return {
        "commands": [c for c in (detect.get("commands") or []) if isinstance(c, str)],
        "markers": [m for m in (detect.get("markers") or []) if isinstance(m, str)],
        "env_vars": [e for e in (detect.get("env") or []) if isinstance(e, str)],
    }


def _check_commands_exist(commands: list[str]) -> list[str]:
    """Check which commands are available in PATH."""
    found: list[str] = []
    for cmd in commands:
        token = _first_token(cmd)
        if shutil.which(token):
            found.append(cmd)
    return found


def _check_markers_exist(project: Path, markers: list[str]) -> list[str]:
    """Check which marker files/dirs exist in the project."""
    return [m for m in markers if (project / m).exists()]


def _check_env_vars_exist(env_vars: list[str]) -> list[str]:
    """Check which environment variables are set."""
    return [e for e in env_vars if os.getenv(e)]


def _build_detection_result(
    item: dict[str, Any],
    available: bool,
    found_commands: list[str],
    found_markers: list[str],
    found_env: list[str],
) -> dict[str, Any]:
    """Build the detection result dictionary for a single tool."""
    return {
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


def detect_tools(project: Path, registry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect available tools from registry definitions."""
    project = project.resolve()
    out: list[dict[str, Any]] = []

    for item in registry:
        config = _extract_detect_config(item)
        found_commands = _check_commands_exist(config["commands"])
        found_markers = _check_markers_exist(project, config["markers"])
        found_env = _check_env_vars_exist(config["env_vars"])

        available = bool(found_commands or found_markers or found_env)

        out.append(
            _build_detection_result(item, available, found_commands, found_markers, found_env),
        )

    return out


def find_tool_entry(registry: list[dict[str, Any]], tool_id: str) -> dict[str, Any] | None:
    """Return a registry entry by id (case-insensitive), or ``None``."""
    target = tool_id.strip().lower()
    for item in registry:
        current = str(item.get("id") or "").strip().lower()
        if current == target:
            return item
    return None


def infer_adapter_kind(tool: dict[str, Any]) -> str:
    """Pick a safe default adapter kind for a tool registry entry."""
    lane = str(tool.get("lane") or "manual")
    category = str(tool.get("category") or "")

    if lane == "manual":
        return "human"
    if category in {"app_builder", "specialist"}:
        return "api"
    return "shell"


def _extract_tool_metadata(tool: dict[str, Any]) -> dict[str, str]:
    """Extract and normalize tool metadata."""
    return {
        "tool_id": str(tool.get("id") or "unknown"),
        "lane": str(tool.get("lane") or "manual"),
        "category": str(tool.get("category") or "unknown"),
        "stability": str(tool.get("stability") or "unknown"),
        "invoke": str(tool.get("invoke") or ""),
        "notes": str(tool.get("notes") or ""),
    }


def _validate_adapter_kind(tool: dict[str, Any], adapter_kind: str | None) -> str:
    """Validate and determine adapter kind."""
    kind = adapter_kind or infer_adapter_kind(tool)
    if kind not in {"human", "shell", "api", "llm"}:
        raise ValueError(f"unsupported adapter kind: {kind}")
    return kind


def _build_scaffold_prompt_lines(
    metadata: dict[str, str],
    plugin_bridge: bool,
    kind: str,
) -> list[str]:
    """Build prompt lines for the scaffold."""
    scaffold_title = "PLUGIN BRIDGE SCAFFOLD" if plugin_bridge else "TOOL ADAPTER SCAFFOLD"
    prompt_lines = [
        f"[{scaffold_title}]",
        f"- tool_id: {metadata['tool_id']}",
        f"- lane: {metadata['lane']}",
        f"- category: {metadata['category']}",
        f"- stability: {metadata['stability']}",
        f"- suggested_executor_kind: {kind}",
    ]
    if metadata["invoke"]:
        prompt_lines.append(f"- invoke_hint: {metadata['invoke']}")
    if metadata["notes"]:
        prompt_lines.append(f"- notes: {metadata['notes']}")

    if plugin_bridge:
        prompt_lines.extend(
            [
                "- bridge_hosts: vscode, jetbrains, zed",
                "- bridge_mode: read-only status first, then explicit invoke actions",
                "- required_next_step: define plugin host + invocation contract before queue run",
            ],
        )
    else:
        prompt_lines.append(
            "- required_next_step: convert this scaffold into concrete "
            "executor inputs before queue run",
        )
    return prompt_lines


def _build_scaffold_labels(metadata: dict[str, str], plugin_bridge: bool) -> list[str]:
    """Build labels for the scaffold."""
    labels = ["adapter-scaffold", f"tool-{metadata['tool_id']}", f"lane-{metadata['lane']}"]
    if plugin_bridge:
        labels.append("plugin-bridge-scaffold")
    return labels


def _build_scaffold_inputs(
    metadata: dict[str, str],
    plugin_bridge: bool,
    kind: str,
) -> dict[str, Any]:
    """Build inputs dict for the scaffold."""
    inputs = {
        "tool_id": metadata["tool_id"],
        "tool_lane": metadata["lane"],
        "tool_category": metadata["category"],
        "tool_stability": metadata["stability"],
        "adapter_executor_hint": kind,
        "tool_invoke_hint": metadata["invoke"],
    }
    if plugin_bridge:
        inputs.update(
            {
                "plugin_bridge": True,
                "plugin_bridge_hosts": ["vscode", "jetbrains", "zed"],
                "plugin_bridge_mode": "read-only-first",
            },
        )
    return inputs


def build_tool_task_scaffold(
    tool: dict[str, Any],
    *,
    adapter_kind: str | None = None,
) -> dict[str, Any]:
    """Build task scaffold payload for ``create_nl_task(..., scaffold=...)``."""
    metadata = _extract_tool_metadata(tool)
    kind = _validate_adapter_kind(tool, adapter_kind)

    plugin_bridge = metadata["category"] == "plugin"
    source_tool = "koru-cli-plugin-bridge" if plugin_bridge else "koru-cli-tool-adapter"

    prompt_lines = _build_scaffold_prompt_lines(metadata, plugin_bridge, kind)
    labels = _build_scaffold_labels(metadata, plugin_bridge)
    inputs = _build_scaffold_inputs(metadata, plugin_bridge, kind)

    return {
        "source_tool": source_tool,
        "source_context": {
            "tool_id": metadata["tool_id"],
            "tool_lane": metadata["lane"],
            "tool_category": metadata["category"],
            "tool_stability": metadata["stability"],
            "adapter_kind": kind,
            "invoke_hint": metadata["invoke"],
            "plugin_bridge": plugin_bridge,
        },
        "labels": labels,
        "inputs": inputs,
        "prompt_suffix": "\n".join(prompt_lines),
    }


def render_tools_detect_text(results: list[dict[str, Any]], *, registry_path: Path | None) -> str:
    """Render a compact text report for ``koru tools detect``."""
    available = sum(1 for r in results if r.get("available"))
    lines = [
        "koru tools detect",
        f"registry: {registry_path if registry_path else '(not found)'}",
        f"summary: total={len(results)} available={available} missing={len(results) - available}",
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
            f"`{r.get('available')}` | `{via}` |",
        )
    return "\n".join(lines)
