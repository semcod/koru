"""Environment probing for Koru autonomy: detect IDE, MCP, autopilot, sockets.

This module is the *single* place that answers questions like:

  - which IDE binaries are installed on this host?
  - is the autopilot daemon socket present + accessible?
  - is MCP configured for any IDE in this project?
  - is this host even capable of GUI bridging (headless probe)?
  - is the stored autopilot socket stale (no listener)?

The probes here are read-only. Auto-repair primitives in
:mod:`koru.autonomy.heal` consume these probes and apply fixes.
"""


import contextlib
import os
import shutil
import socket as _socket
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from koru.ide_router import is_headless_environment

KNOWN_IDES = ("cursor", "windsurf", "vscode", "code", "code-oss", "vscodium", "zed")


@dataclass(frozen=True)
class IDEPresence:
    """Per-IDE detection result."""

    ide: str
    binary_path: str | None
    mcp_config_path: Path | None
    mcp_has_koru: bool

    @property
    def installed(self) -> bool:
        return self.binary_path is not None


@dataclass(frozen=True)
class SocketHealth:
    """State of a Unix-socket file (typically autopilot)."""

    path: Path
    exists: bool
    listening: bool
    stale: bool  # exists but no listener — safe to remove

    @property
    def healthy(self) -> bool:
        return self.exists and self.listening


@dataclass(frozen=True)
class EnvironmentReport:
    """Snapshot of the autonomy-relevant environment.

    Designed to be cheap (<200 ms) so it can be called on every cycle.
    """

    headless: bool
    ides: list[IDEPresence] = field(default_factory=list)
    autopilot_socket: SocketHealth | None = None
    can_use_plugin_socket: bool = False
    can_use_mcp: bool = False
    fixable_issues: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def installed_ides(self) -> list[str]:
        return [p.ide for p in self.ides if p.installed]

    @property
    def mcp_enabled_ides(self) -> list[str]:
        return [p.ide for p in self.ides if p.mcp_has_koru]


def probe_ide_presence(
    project: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> list[IDEPresence]:
    """Detect which IDE binaries are installed + whether MCP is configured.

    Returns one entry per known IDE so a caller can also see *negatives*.
    """
    env = os.environ if environ is None else environ
    import json

    from koru.mcp_provision import (
        _cursor_project_config,
        _vscode_project_config,
        _windsurf_global_config,
        _windsurf_project_config,
    )

    mcp_paths = {
        "cursor": _cursor_project_config(project),
        "vscode": _vscode_project_config(project),
        "windsurf": _windsurf_project_config(project),
    }
    windsurf_global = _windsurf_global_config()

    out: list[IDEPresence] = []
    for ide in KNOWN_IDES:
        # `code-oss`/`vscodium` share VS Code's mcp config slot
        cfg_key = "vscode" if ide in ("code", "code-oss", "vscodium") else ide
        cfg_path = mcp_paths.get(cfg_key)
        mcp_has_koru = False
        chosen_path: Path | None = None
        for candidate in [cfg_path, windsurf_global if cfg_key == "windsurf" else None]:
            if candidate is None or not candidate.is_file():
                continue
            chosen_path = candidate
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                servers = data.get("mcpServers") if isinstance(data, dict) else None
                if isinstance(servers, dict) and "koru" in servers:
                    koru = servers["koru"]
                    if not (isinstance(koru, dict) and koru.get("disabled") is True):
                        mcp_has_koru = True
                        break
            except (OSError, ValueError):
                continue

        binary = shutil.which(ide, path=env.get("PATH"))
        out.append(
            IDEPresence(
                ide=ide,
                binary_path=binary,
                mcp_config_path=chosen_path,
                mcp_has_koru=mcp_has_koru,
            ),
        )
    return out


def probe_socket_health(path: Path, *, connect_timeout: float = 0.5) -> SocketHealth:
    """Connect-probe a Unix socket. Detects stale sockets safely.

    A socket is *stale* when the file exists but `connect()` fails with
    ``ECONNREFUSED`` / ``ENOTSOCK`` — i.e. nothing is listening.
    """
    if not path.exists():
        return SocketHealth(path=path, exists=False, listening=False, stale=False)

    sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    sock.settimeout(connect_timeout)
    try:
        sock.connect(str(path))
        sock.close()
        return SocketHealth(path=path, exists=True, listening=True, stale=False)
    except (ConnectionRefusedError, FileNotFoundError):
        # File exists but no listener → stale
        return SocketHealth(path=path, exists=True, listening=False, stale=True)
    except TimeoutError:
        # Busy daemon or slow accept — do not unlink the socket file.
        return SocketHealth(path=path, exists=True, listening=False, stale=False)
    except OSError as exc:
        # Only treat definitive "nothing listening" as stale.
        if getattr(exc, "errno", None) in {111, 2}:  # ECONNREFUSED, ENOENT
            return SocketHealth(path=path, exists=True, listening=False, stale=True)
        return SocketHealth(path=path, exists=True, listening=False, stale=False)
    finally:
        with contextlib.suppress(OSError):
            sock.close()


def _check_socket_health(autopilot_socket: Path | None) -> SocketHealth | None:
    """Check autopilot socket health if socket path is provided."""
    if autopilot_socket is not None:
        return probe_socket_health(autopilot_socket)
    return None


def _build_fixable_issues(
    socket_health: SocketHealth | None,
    ides: list[IDEPresence],
) -> list[str]:
    """Build list of fixable environment issues."""
    fixable: list[str] = []
    if socket_health and socket_health.stale:
        fixable.append(
            f"stale autopilot socket at {socket_health.path}: remove + restart daemon",
        )
    installed = [p.ide for p in ides if p.installed]
    mcp_on = [p.ide for p in ides if p.mcp_has_koru]
    if installed and not mcp_on:
        fixable.append(
            f"IDE(s) installed ({', '.join(installed)}) but Koru MCP is not configured: "
            "run `koru init-ide` / `task koru:mcp:bootstrap`",
        )
    return fixable


def _build_notes(
    headless: bool,
    ides: list[IDEPresence],
) -> list[str]:
    """Build list of environment notes."""
    notes: list[str] = []
    installed = [p.ide for p in ides if p.installed]
    if headless:
        notes.append("headless environment: prefer queue/CLI; autopilot drive is disabled")
    elif not installed:
        notes.append("no known IDE binary on PATH; install cursor/windsurf/vscode or run headless")
    return notes


def probe_environment(
    project: Path,
    *,
    autopilot_socket: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> EnvironmentReport:
    """Single entry point for "what does this host look like right now?"."""
    env = os.environ if environ is None else environ
    headless = is_headless_environment(env)
    ides = probe_ide_presence(project, environ=env)

    socket_health = _check_socket_health(autopilot_socket)
    can_plugin = bool(socket_health and socket_health.listening)
    can_mcp = any(p.mcp_has_koru for p in ides)

    fixable = _build_fixable_issues(socket_health, ides)
    notes = _build_notes(headless, ides)

    return EnvironmentReport(
        headless=headless,
        ides=ides,
        autopilot_socket=socket_health,
        can_use_plugin_socket=can_plugin,
        can_use_mcp=can_mcp,
        fixable_issues=fixable,
        notes=notes,
    )


__all__ = [
    "EnvironmentReport",
    "IDEPresence",
    "KNOWN_IDES",
    "SocketHealth",
    "probe_environment",
    "probe_ide_presence",
    "probe_socket_health",
]
