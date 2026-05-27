"""Experimental registry of IDE / LLM *agent backend* profiles.

This module does **not** perform injection — it documents which transports
exist today and which capabilities are realistic per backend.  Runtime
:class:`~koru.agent_backend_runtime.AgentBackend` implementations live in
:mod:`koru.agent_backend_runtime`.  Use profiles from docs, tests, and config
validation; use the runtime module from :mod:`koru.autonomous` and future
executors.

See: ``docs/agent-backends-architecture.md``.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml


@dataclass(frozen=True)
class AgentBackendProfile:
    """Static description of one way koru can reach an IDE-side agent."""

    id: str
    transport: str
    can_push_chat: bool
    can_pull_chat_text: bool
    needs_gui_session: bool
    mcp_tools_only: bool
    primary_code: str


_PROFILES: Final[tuple[AgentBackendProfile, ...]] = (
    AgentBackendProfile(
        id="vscode_family_plugin_socket",
        transport="unix_socket + VS Code extension (VSIX)",
        can_push_chat=True,
        can_pull_chat_text=False,
        needs_gui_session=True,
        mcp_tools_only=False,
        primary_code="plugins/koru-autopilot-vscode/",
    ),
    AgentBackendProfile(
        id="jetbrains_plugin_socket",
        transport="unix_socket + IntelliJ plugin",
        can_push_chat=True,
        can_pull_chat_text=False,
        needs_gui_session=True,
        mcp_tools_only=False,
        primary_code="plugins/koru-autopilot-jetbrains/",
    ),
    AgentBackendProfile(
        id="mcp_stdio_server",
        transport="MCP stdio (IDE is client)",
        can_push_chat=False,
        can_pull_chat_text=False,
        needs_gui_session=False,
        mcp_tools_only=True,
        primary_code="src/koru/mcp_server.py",
    ),
    AgentBackendProfile(
        id="os_keyboard_injector",
        transport="xdotool / wtype / ydotool / clipboard",
        can_push_chat=True,
        can_pull_chat_text=False,
        needs_gui_session=True,
        mcp_tools_only=False,
        primary_code="src/koru/autopilot/injector.py",
    ),
    AgentBackendProfile(
        id="vendor_agent_cli",
        transport="subprocess (cursor agent, claude, …)",
        can_push_chat=True,
        can_pull_chat_text=False,
        needs_gui_session=False,
        mcp_tools_only=False,
        primary_code="src/koru/queue.py (run_process pattern)",
    ),
)

# Short names used in ``koru.yaml`` ``ide_integration.lanes.*.backend``.
_BACKEND_ALIASES: Final[dict[str, str]] = {
    "plugin_socket": "vscode_family_plugin_socket",
    "mcp_tool": "mcp_stdio_server",
    "os_injector": "os_keyboard_injector",
}


def normalize_agent_backend_id(raw: str) -> str:
    """Map alias / shorthand to a canonical :attr:`AgentBackendProfile.id`."""
    key = raw.strip().lower().replace("-", "_")
    if key in _BACKEND_ALIASES:
        return _BACKEND_ALIASES[key]
    for profile in _PROFILES:
        if profile.id == key:
            return profile.id
    return key


def list_agent_backend_ids() -> tuple[str, ...]:
    """Return stable backend profile ids (for config validation / docs)."""
    return tuple(p.id for p in _PROFILES)


def iter_agent_backend_profiles() -> tuple[AgentBackendProfile, ...]:
    """Return every registered profile (stable order)."""
    return _PROFILES


def get_agent_backend_profile(backend_id: str) -> AgentBackendProfile | None:
    """Return a profile or ``None`` if *backend_id* is unknown."""
    nid = normalize_agent_backend_id(backend_id)
    for p in _PROFILES:
        if p.id == nid:
            return p
    return None


@dataclass(frozen=True)
class LaneConfig:
    """One lane entry under ``koru.yaml`` ``ide_integration.lanes``."""

    backend: str
    ide: str | None = None
    socket: str | None = None
    mcp_server: str | None = None
    prompt_mode: str | None = None


@dataclass(frozen=True)
class AgentIntegrationConfig:
    """Parsed ``ide_integration`` block from a project ``koru.yaml``."""

    default_lane: str
    lanes: dict[str, LaneConfig]


def _parse_lane(raw: Any) -> LaneConfig | None:
    if not isinstance(raw, dict):
        return None
    backend_value = raw.get("backend")
    if not isinstance(backend_value, str) or not backend_value.strip():
        return None
    ide = raw.get("ide")
    socket = raw.get("socket")
    mcp_server = raw.get("mcp_server")
    prompt_mode = raw.get("prompt_mode")
    return LaneConfig(
        backend=normalize_agent_backend_id(backend_value),
        ide=ide if isinstance(ide, str) else None,
        socket=socket if isinstance(socket, str) else None,
        mcp_server=mcp_server if isinstance(mcp_server, str) else None,
        prompt_mode=prompt_mode if isinstance(prompt_mode, str) else None,
    )


def load_agent_integration_config(project: Path) -> AgentIntegrationConfig | None:
    """Load ``ide_integration`` from ``<project>/koru.yaml`` if present."""
    path = project / "koru.yaml"
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    block = data.get("ide_integration")
    if not isinstance(block, dict):
        return None
    default_lane = block.get("default_lane")
    if not isinstance(default_lane, str) or not default_lane.strip():
        return None
    raw_lanes = block.get("lanes")
    if not isinstance(raw_lanes, dict):
        return AgentIntegrationConfig(default_lane=default_lane.strip(), lanes={})
    lanes: dict[str, LaneConfig] = {}
    for name, raw in raw_lanes.items():
        if not isinstance(name, str):
            continue
        lane = _parse_lane(raw)
        if lane is not None:
            lanes[name.strip()] = lane
    return AgentIntegrationConfig(default_lane=default_lane.strip(), lanes=lanes)


def validate_agent_integration_config(config: AgentIntegrationConfig | None) -> list[str]:
    """Return human-readable validation errors (empty list when OK)."""
    if config is None:
        return []
    errors: list[str] = []
    if config.default_lane not in config.lanes:
        errors.append(
            f"default_lane '{config.default_lane}' is not defined in lanes",
        )
    for lane_name, lane in config.lanes.items():
        if get_agent_backend_profile(lane.backend) is None:
            errors.append(
                f"lane '{lane_name}' uses unknown backend '{lane.backend}'",
            )
    return errors


__all__ = [
    "AgentBackendProfile",
    "AgentIntegrationConfig",
    "LaneConfig",
    "get_agent_backend_profile",
    "iter_agent_backend_profiles",
    "list_agent_backend_ids",
    "load_agent_integration_config",
    "normalize_agent_backend_id",
    "validate_agent_integration_config",
]
