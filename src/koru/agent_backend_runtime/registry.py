"""Lane → backend resolution for :mod:`koru.agent_backend_runtime`."""

import os
from pathlib import Path

from koru.agent_backend_runtime.backends import (
    GillmGuiBackend,
    ImglDesktopBackend,
    McpToolBackend,
    Nlp2UriDesktopBackend,
    NoopBackend,
    OsInjectorBackend,
    PluginSocketBackend,
    TillmShellBackend,
    VdisplayControlBackend,
)
from koru.agent_backend_runtime.base import AgentBackend
from koru.agent_backends import normalize_agent_backend_id
from koru.ide_adapters.gillm_client import build_gillm_ide_client
from koru.ide_client import IDEControlClient


def _build_plugin_socket_backend(client: IDEControlClient | None = None) -> AgentBackend:
    if client is None:
        raise ValueError("plugin_socket backend requires an IDEControlClient")
    return PluginSocketBackend(client=client)


def _build_mcp_tool_backend(mcp_server: str | None = None) -> AgentBackend:
    return McpToolBackend(mcp_server=mcp_server)


def _build_vendor_agent_cli_backend(shell_client_id: str | None = None) -> AgentBackend:
    return TillmShellBackend(
        client_id=shell_client_id or os.environ.get("KORU_TILLM_CLIENT", "aider"),
        execute=os.environ.get("KORU_TILLM_DRY_RUN", "").strip().lower() not in {"1", "true", "yes", "on"},
    )


def _build_gillm_gui_backend() -> AgentBackend:
    return GillmGuiBackend(client=build_gillm_ide_client())


def _build_os_injector_backend() -> AgentBackend:
    profile = os.environ.get("KORU_OS_INJECTOR_PROFILE", "").strip()
    if not profile:
        raise ValueError("os_injector backend requires KORU_OS_INJECTOR_PROFILE")
    raw_cfg = os.environ.get("KORU_OS_INJECTOR_CONFIG", "").strip()
    cfg = Path(raw_cfg).expanduser().resolve() if raw_cfg else None
    return OsInjectorBackend(profile_id=profile, config_path=cfg)


def _build_nlp2uri_desktop_backend() -> AgentBackend:
    dry = os.environ.get("KORU_NLP2URI_DRY_RUN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return Nlp2UriDesktopBackend(dry_run=dry)


def _build_imgl_desktop_backend() -> AgentBackend:
    dry = os.environ.get("KORU_IMGL_DRY_RUN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return ImglDesktopBackend(dry_run=dry)


def _build_vdisplay_control_backend() -> AgentBackend:
    dry = os.environ.get("KORU_VDISPLAY_DRY_RUN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return VdisplayControlBackend(dry_run=dry)


def _build_noop_backend(noop_reason: str) -> AgentBackend:
    return NoopBackend(reason=noop_reason)


_BACKEND_BUILDERS = {
    "plugin_socket": _build_plugin_socket_backend,
    "vscode_family_plugin_socket": _build_plugin_socket_backend,
    "mcp_tool": _build_mcp_tool_backend,
    "mcp_stdio_server": _build_mcp_tool_backend,
    "vendor_agent_cli": _build_vendor_agent_cli_backend,
    "gillm_gui": _build_gillm_gui_backend,
    "gillm_gui_driver": _build_gillm_gui_backend,
    "os_injector": _build_os_injector_backend,
    "os_keyboard_injector": _build_os_injector_backend,
    "nlp2uri_desktop": _build_nlp2uri_desktop_backend,
    "nlp2uri_desktop_window": _build_nlp2uri_desktop_backend,
    "imgl": _build_imgl_desktop_backend,
    "imgl_vision": _build_imgl_desktop_backend,
    "imgl_desktop": _build_imgl_desktop_backend,
    "imgl_vision_driver": _build_imgl_desktop_backend,
    "vdisplay": _build_vdisplay_control_backend,
    "vdisplay_control": _build_vdisplay_control_backend,
    "vdisplay_semantic_control": _build_vdisplay_control_backend,
    "none": _build_noop_backend,
    "noop": _build_noop_backend,
    "": _build_noop_backend,
}


def build_agent_backend(
    *,
    backend_id: str,
    client: IDEControlClient | None = None,
    mcp_server: str | None = None,
    noop_reason: str = "headless",
    shell_client_id: str | None = None,
) -> AgentBackend:
    """Resolve a lane backend id into a concrete :class:`AgentBackend`.

    Lane ids follow :mod:`koru.agent_backends` (``plugin_socket``,
    ``mcp_tool``, ``os_injector``, ``none``).
    """
    bid = (backend_id or "").strip().lower().replace("-", "_")
    normalized = normalize_agent_backend_id(backend_id or "")
    builder = _BACKEND_BUILDERS.get(bid) or _BACKEND_BUILDERS.get(normalized)
    if builder:
        if "client" in builder.__code__.co_varnames:
            return builder(client=client)
        elif "mcp_server" in builder.__code__.co_varnames:
            return builder(mcp_server=mcp_server)
        elif "shell_client_id" in builder.__code__.co_varnames:
            return builder(shell_client_id=shell_client_id)
        elif "noop_reason" in builder.__code__.co_varnames:
            return builder(noop_reason=noop_reason)
        else:
            return builder()
    raise ValueError(f"unknown agent backend id: {backend_id!r}")
