"""Concrete :class:`AgentBackend` implementations."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from gillm.injection.os_injector import (
        OsInjectorError,
        inject_with_profile,
        load_profile,
    )
except ImportError:  # gillm optional — OsInjectorBackend degrades to a soft error

    class OsInjectorError(Exception):  # type: ignore[no-redef]
        """Raised when gillm's OS injector is unavailable on this host."""

    def load_profile(profile_id: str, config_path: Any = None) -> Any:  # type: ignore[misc]
        raise OsInjectorError("gillm is not installed; os_injector backend unavailable (pip install gillm)")

    def inject_with_profile(*, profile: Any, text: str, submit: bool, dry_run: bool = False) -> Any:  # type: ignore[misc]
        raise OsInjectorError("gillm is not installed; os_injector backend unavailable (pip install gillm)")


from koru.ide_adapters.gillm_client import GillmIDEControlClient
from koru.ide_adapters.gillm_recovery import enrich_drive_reply_with_recovery
from koru.ide_client import IDEControlClient
from koru.tillm_bridge import drive_shell_chat


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
        del ide, ticket_id
        try:
            return drive_shell_chat(
                client_id=self.client_id,
                project=project,
                prompt=prompt,
                execute=self.execute and submit,
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


def _nlp2uri_desktop_send(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Focus IDE window via nlp2uri, then type text via gillm Injector."""
    try:
        from nlp2uri import compile_uri_to_actions, execute_uri  # noqa: F401
        from nlp2uri.models import HostPlatform
    except ImportError:
        return {
            "ok": False,
            "backend": "nlp2uri_desktop",
            "message": "nlp2uri is not installed. Install with: pip install 'koru[desktop]'",
            "type": "error",
        }

    from koruide.ide import ide_window_name

    window_name = ide_window_name(ide)
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
