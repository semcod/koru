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


import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from gillm.injection.os_injector import OsInjectorError, inject_with_profile, load_profile

from koru.agent_backends import normalize_agent_backend_id
from koru.ide_adapters.gillm_client import GillmIDEControlClient, build_gillm_ide_client
from koru.ide_adapters.gillm_recovery import enrich_drive_reply_with_recovery
from koru.ide_client import IDEControlClient
from koru.tillm_bridge import drive_shell_chat


class AgentBackend(Protocol):
    """Push a prompt toward the agent UI (chat / drive session) for this project."""

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        """Return the same shape as :meth:`IDEControlClient.drive` (``ok``, ``message``, …)."""
        ...


@dataclass
class PluginSocketBackend:
    """Plugin + unix socket — maps ``send_chat`` to autopilot ``drive``."""

    client: IDEControlClient

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del project, ticket_id  # reserved for future routing / logging
        return self.client.drive(prompt, submit=submit, ide=ide)


@dataclass
class McpToolBackend:
    """MCP-only backend (e.g. Cursor with koru_run_ticket).

    No socket / plugin: the LLM in the IDE is expected to call MCP tools on
    its own. ``send_chat`` is a no-op that returns ``ok=True`` with a marker
    so the autonomy loop keeps running and prompts are still emitted to the
    event stream / logs.
    """

    mcp_server: str | None = None

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del project, prompt, ide, submit, ticket_id
        # IDE LLM drives itself via MCP; nothing to push from autonomy side.
        return {
            "ok": True,
            "message": "mcp_tool: prompt logged; LLM drives via MCP tools",
            "backend": "mcp_tool",
            "mcp_server": self.mcp_server,
        }


@dataclass
class NoopBackend:
    """Explicit no-op backend for headless / smoke / CI runs."""

    reason: str = "headless"

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del project, prompt, ide, submit, ticket_id
        return {
            "ok": True,
            "message": f"noop ({self.reason})",
            "backend": "noop",
        }


@dataclass
class TillmShellBackend:
    """Shell LLM client backend delegated to the external ``tillm`` package."""

    client_id: str = "aider"
    execute: bool = True

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del ide, submit, ticket_id
        try:
            return drive_shell_chat(
                client_id=self.client_id,
                project=project,
                prompt=prompt,
                execute=self.execute,
            )
        except Exception as exc:
            return {
                "ok": False,
                "backend": "tillm_shell",
                "client_id": self.client_id,
                "message": str(exc),
                "type": "error",
            }


@dataclass
class OsInjectorBackend:
    """Coordinate-based fallback backend (X11 + xdotool)."""

    profile_id: str
    config_path: Path | None = None

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del project, ide, ticket_id
        try:
            profile = load_profile(self.profile_id, config_path=self.config_path)
            return inject_with_profile(profile=profile, text=prompt, submit=submit, dry_run=False)
        except OsInjectorError as exc:
            return {"ok": False, "backend": "os_injector", "message": str(exc), "type": "error"}


@dataclass
class GillmGuiBackend:
    """Gillm GuiDriver backend — profile/keyboard fallback without plugin socket."""

    client: GillmIDEControlClient

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del project, ticket_id
        reply = self.client.drive(prompt, submit=submit, ide=ide)
        if not reply.get("ok"):
            enrich_drive_reply_with_recovery(reply)
        return reply


@dataclass
class ImglDesktopBackend:
    """Vision-guided UI backend via imgl (nlp2imgl / rest2imgl).

    Captures screen, resolves UI elements from catalog, types into Chat input
    and submits via KEY — fallback when koruide plugin socket is unavailable.
    """

    dry_run: bool = False

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del project, ticket_id
        from koru.integrations.imgl_client import imgl_available, imgl_missing_message, send_chat

        if self.dry_run:
            return send_chat(prompt, ide=ide, submit=submit, dry_run=True)
        if not imgl_available():
            return {
                "ok": False,
                "backend": "imgl",
                "message": imgl_missing_message(),
                "type": "error",
            }
        return send_chat(prompt, ide=ide, submit=submit, dry_run=False)


@dataclass
class VdisplayControlBackend:
    """Semantic desktop/browser/terminal control via vdisplay control plane."""

    dry_run: bool = False

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del project, ticket_id
        from koru.integrations.vdisplay_client import send_chat

        return send_chat(prompt, ide=ide, submit=submit, dry_run=self.dry_run)


@dataclass
class Nlp2UriDesktopBackend:
    """Window-management backend via nlp2uri desktop-window://focus.

    Uses nlp2uri to focus the IDE window through proper window management
    (wmctrl -a / xdotool search --name ... windowactivate) instead of
    coordinate-based mouse clicks.  After focus, delegates text injection
    to :class:`gillm.injection.injector.Injector`.
    """

    dry_run: bool = False

    def send_chat(
        self,
        project: Path,
        prompt: str,
        *,
        ide: str,
        submit: bool,
        ticket_id: str | None = None,
    ) -> dict[str, Any]:
        del project, ticket_id
        return _nlp2uri_desktop_send(prompt, ide=ide, submit=submit, dry_run=self.dry_run)


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
    if bid == "plugin_socket" or normalized == "vscode_family_plugin_socket":
        if client is None:
            raise ValueError("plugin_socket backend requires an IDEControlClient")
        return PluginSocketBackend(client=client)
    if bid == "mcp_tool" or normalized == "mcp_stdio_server":
        return McpToolBackend(mcp_server=mcp_server)
    if normalized == "vendor_agent_cli":
        return TillmShellBackend(
            client_id=shell_client_id or os.environ.get("KORU_TILLM_CLIENT", "aider"),
            execute=os.environ.get("KORU_TILLM_DRY_RUN", "").strip().lower()
            not in {"1", "true", "yes", "on"},
        )
    if bid == "gillm_gui" or normalized == "gillm_gui_driver":
        return GillmGuiBackend(client=build_gillm_ide_client())
    if bid == "os_injector" or normalized == "os_keyboard_injector":
        profile = os.environ.get("KORU_OS_INJECTOR_PROFILE", "").strip()
        if not profile:
            raise ValueError("os_injector backend requires KORU_OS_INJECTOR_PROFILE")
        raw_cfg = os.environ.get("KORU_OS_INJECTOR_CONFIG", "").strip()
        cfg = Path(raw_cfg).expanduser().resolve() if raw_cfg else None
        return OsInjectorBackend(profile_id=profile, config_path=cfg)
    if bid == "nlp2uri_desktop" or normalized == "nlp2uri_desktop_window":
        dry = os.environ.get("KORU_NLP2URI_DRY_RUN", "").strip().lower() in {
            "1", "true", "yes", "on",
        }
        return Nlp2UriDesktopBackend(dry_run=dry)
    if bid in ("imgl", "imgl_vision", "imgl_desktop") or normalized == "imgl_vision_driver":
        dry = os.environ.get("KORU_IMGL_DRY_RUN", "").strip().lower() in {
            "1", "true", "yes", "on",
        }
        return ImglDesktopBackend(dry_run=dry)
    if bid in ("vdisplay", "vdisplay_control") or normalized == "vdisplay_semantic_control":
        dry = os.environ.get("KORU_VDISPLAY_DRY_RUN", "").strip().lower() in {
            "1", "true", "yes", "on",
        }
        return VdisplayControlBackend(dry_run=dry)
    if bid in ("none", "noop", ""):
        return NoopBackend(reason=noop_reason)
    raise ValueError(f"unknown agent backend id: {backend_id!r}")


def _nlp2uri_desktop_send(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Focus IDE window via nlp2uri, then type text via gillm Injector."""
    try:
        from nlp2uri import compile_uri_to_actions, execute_uri
        from nlp2uri.models import HostPlatform
    except ImportError:
        return {
            "ok": False,
            "backend": "nlp2uri_desktop",
            "message": "nlp2uri is not installed. Install with: pip install 'koru[desktop]'",
            "type": "error",
        }

    # Map koru IDE ids to window names that wmctrl/xdotool can find.
    _IDE_WINDOW_NAMES: dict[str, str] = {
        "antigravity": "antigravity",
        "vscode": "Visual Studio Code",
        "vscodium": "VSCodium",
        "cursor": "Cursor",
        "windsurf": "Windsurf",
        "jetbrains": "JetBrains",
        "zed": "Zed",
    }
    window_name = _IDE_WINDOW_NAMES.get(ide, ide)
    focus_uri = f"desktop-window://focus?name={window_name}"

    if dry_run:
        return {
            "ok": True,
            "backend": "nlp2uri_desktop",
            "dry_run": True,
            "focus_uri": focus_uri,
            "ide": ide,
            "chars": len(prompt),
            "submit": submit,
        }

    # Step 1: Focus the IDE window via nlp2uri.
    try:
        focus_result = execute_uri(focus_uri, platform=HostPlatform.LINUX, dry_run=False)
        focus_ok = focus_result.ok
    except Exception as exc:
        focus_ok = False
        focus_error = str(exc)
        return {
            "ok": False,
            "backend": "nlp2uri_desktop",
            "message": f"nlp2uri focus failed: {focus_error}",
            "focus_uri": focus_uri,
            "type": "error",
        }

    # Step 2: Small delay for window manager to complete the focus switch.
    import time
    time.sleep(0.3)

    # Step 3: Type text via gillm Injector.
    try:
        from gillm.injection.injector import Injector

        injector = Injector()
        result = injector.type_text(prompt, ide=ide, submit=submit)
        return {
            "ok": True,
            "backend": "nlp2uri_desktop",
            "focus_uri": focus_uri,
            "focus_ok": focus_ok,
            "injection_backend": result.backend,
            "submitted": result.submitted,
            "ide": ide,
        }
    except Exception as exc:
        return {
            "ok": False,
            "backend": "nlp2uri_desktop",
            "message": f"text injection failed after focus: {exc}",
            "focus_uri": focus_uri,
            "focus_ok": focus_ok,
            "type": "error",
        }


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
