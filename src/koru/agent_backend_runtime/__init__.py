"""Runtime *agent UI* backends — how ``autonomous`` reaches an IDE-side LLM.

Static capability profiles live in :mod:`koru.agent_backends`; this module holds
the small :class:`AgentBackend` protocol and concrete implementations:

  * :class:`PluginSocketBackend` — IDE plugin + unix socket (windsurf, vscode,
    cursor, jetbrains via koru-autopilot plugin).
  * :class:`McpToolBackend` — MCP tool path (Cursor / any MCP-aware IDE that
    runs ``koru mcp-server runstdio``); send_chat is a no-op since the LLM is
    expected to call ``koru_run_ticket`` itself. Used to keep the autonomy
    loop running when no plugin socket is available.
  * :class:`NoopBackend` — explicit "headless / smoke" backend; useful for CI
    and `--no-autopilot` smoke tests.
  * :class:`TillmShellBackend` — shell LLM client via the external ``tillm``
    plugin/package (aider, Claude Code, Codex CLI, Devin, ...).

Lane → backend resolution lives in :func:`build_agent_backend`.
"""

from koru.agent_backend_runtime.backends import (
    GillmGuiBackend,
    ImglDesktopBackend,
    McpToolBackend,
    Nlp2UriDesktopBackend,
    NoopBackend,
    OsInjectorBackend,
    PluginSocketBackend,
    TillmShellBackend,
)
from koru.agent_backend_runtime.backends import (
    VdisplayControlBackend as VdisplayControlBackend,
)
from koru.agent_backend_runtime.backends import (
    _nlp2uri_desktop_send as _nlp2uri_desktop_send,
)
from koru.agent_backend_runtime.base import AgentBackend
from koru.agent_backend_runtime.registry import build_agent_backend

__all__ = [
    "AgentBackend",
    "PluginSocketBackend",
    "McpToolBackend",
    "TillmShellBackend",
    "GillmGuiBackend",
    "ImglDesktopBackend",
    "OsInjectorBackend",
    "Nlp2UriDesktopBackend",
    "NoopBackend",
    "build_agent_backend",
]
