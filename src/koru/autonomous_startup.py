"""Startup IDE / environment probe for ``koru autonomous up``."""


import importlib.metadata
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from koru.autopilot import default_socket_path
from koru.autopilot.ide import (
    detect_running_ides,
    detect_terminal_host_ide_id,
    pick_target,
)
from koru.ide_router import is_headless_environment, resolve_ide_route

_PLUGIN_IDE_LANES = frozenset({"windsurf", "vscode", "cursor", "jetbrains", "zed"})
_AUTOPILOT_PLUGIN_LANES = ("cursor", "windsurf", "vscode")


def koru_distribution_version() -> str:
    try:
        return importlib.metadata.version("koru")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _session_label() -> str:
    if (os.environ.get("WAYLAND_DISPLAY") or "").strip():
        return "wayland"
    if (os.environ.get("DISPLAY") or "").strip():
        return "x11"
    return "headless"


def _terminal_agent_lane_from_env() -> str | None:
    host = detect_terminal_host_ide_id()
    if host:
        return host
    explicit = (os.environ.get("KORU_AUTOPILOT_IDE") or "").strip().lower()
    if explicit and explicit != "auto":
        return explicit
    return None


def resolve_agent_lane_id(
    project: Path,
    agent_lane_cli: str,
    *,
    resolve_project_lane,
) -> tuple[str | None, str]:
    """Resolve ``--agent-lane``; return ``(lane_id, source_label)``."""
    raw = (agent_lane_cli or "auto").strip().lower()
    if raw == "none":
        return None, "cli:none"
    if raw != "auto":
        lane = resolve_project_lane(project, raw)
        return lane, f"cli:{raw}"

    terminal = _terminal_agent_lane_from_env()
    if terminal in _PLUGIN_IDE_LANES:
        lane = resolve_project_lane(project, terminal)
        return lane, "terminal"
    if terminal:
        running = detect_running_ides()
        for alt in _AUTOPILOT_PLUGIN_LANES:
            if any(ide.id == alt for ide in running):
                lane = resolve_project_lane(project, alt)
                return lane, f"terminal:prefer-{alt}-over-{terminal}"

    running = detect_running_ides()
    if running:
        picked = pick_target(running)
        if picked is not None:
            return picked.id, f"running:{picked.label}"

    marker = resolve_project_lane(project, "auto")
    return marker, "project-markers"


def resolve_autopilot_ide_for_autonomous(
    autopilot_ide_cli: str,
    lane: str | None,
    *,
    resolve_ide_route_fn,
    detect_running_ides_fn=detect_running_ides,
) -> tuple[str, str]:
    """Return ``(autopilot_ide, source_label)`` aligned with the resolved lane."""
    raw = (autopilot_ide_cli or "auto").strip().lower()
    if raw != "auto":
        route = resolve_ide_route_fn(cli_autopilot_ide=raw)
        return route.autopilot_ide, f"cli:{raw}"
    if lane in _PLUGIN_IDE_LANES:
        return lane, "lane"
    route = resolve_ide_route_fn(cli_autopilot_ide="auto")
    return route.autopilot_ide, "router:auto"


@dataclass(frozen=True)
class AutonomousStartupProbe:
    koru_version: str
    python_version: str
    project: Path
    agent_lane_cli: str
    autopilot_ide_cli: str
    resolved_lane: str | None
    lane_source: str
    resolved_autopilot_ide: str
    autopilot_ide_source: str
    running_ides: tuple[str, ...]
    terminal_lane: str | None
    socket_path: str
    session: str
    term_program: str
    headless: bool
    xdg_runtime_dir: str


def build_startup_probe(
    project: Path,
    *,
    agent_lane_cli: str,
    autopilot_ide_cli: str,
    resolve_project_lane,
    resolve_ide_route_fn=resolve_ide_route,
) -> AutonomousStartupProbe:
    lane, lane_source = resolve_agent_lane_id(
        project,
        agent_lane_cli,
        resolve_project_lane=resolve_project_lane,
    )
    autopilot_ide, ide_source = resolve_autopilot_ide_for_autonomous(
        autopilot_ide_cli,
        lane,
        resolve_ide_route_fn=resolve_ide_route_fn,
    )
    running = detect_running_ides()
    running_labels = tuple(f"{ide.label} (pid={ide.pid})" for ide in running)
    return AutonomousStartupProbe(
        koru_version=koru_distribution_version(),
        python_version=sys.version.split()[0],
        project=project.resolve(),
        agent_lane_cli=(agent_lane_cli or "auto").strip().lower(),
        autopilot_ide_cli=(autopilot_ide_cli or "auto").strip().lower(),
        resolved_lane=lane,
        lane_source=lane_source,
        resolved_autopilot_ide=autopilot_ide,
        autopilot_ide_source=ide_source,
        running_ides=running_labels,
        terminal_lane=_terminal_agent_lane_from_env(),
        socket_path=str(default_socket_path()),
        session=_session_label(),
        term_program=(os.environ.get("TERM_PROGRAM") or "").strip() or "-",
        headless=is_headless_environment(),
        xdg_runtime_dir=(os.environ.get("XDG_RUNTIME_DIR") or "").strip() or "-",
    )


def format_startup_banner(probe: AutonomousStartupProbe) -> list[str]:
    lines = [
        f"koru autonomous: koru {probe.koru_version} (python {probe.python_version})",
        f"koru autonomous: project {probe.project}",
        f"koru autonomous: session={probe.session} TERM_PROGRAM={probe.term_program} "
        f"XDG_RUNTIME_DIR={probe.xdg_runtime_dir}",
    ]
    if probe.running_ides:
        lines.append("koru autonomous: running IDEs: " + "; ".join(probe.running_ides))
    else:
        lines.append("koru autonomous: running IDEs: (none detected)")
    if probe.terminal_lane:
        lines.append(f"koru autonomous: terminal hint → {probe.terminal_lane}")
    lines.append(
        f"koru autonomous: lane={probe.resolved_lane or 'none'} "
        f"(from {probe.lane_source}, cli --agent-lane={probe.agent_lane_cli})",
    )
    lines.append(
        f"koru autonomous: autopilot IDE={probe.resolved_autopilot_ide} "
        f"(from {probe.autopilot_ide_source}, cli --autopilot-ide={probe.autopilot_ide_cli})",
    )
    lines.append(f"koru autonomous: autopilot socket → {probe.socket_path}")
    if probe.headless:
        lines.append(
            "koru autonomous: headless environment — plugin drive disabled unless "
            "KORU_HEADLESS_ALLOW_AUTOPILOT=1",
        )
    return lines


def format_post_startup_operator_hints(
    probe: AutonomousStartupProbe,
    *,
    plugin_connected: bool | None = None,
) -> list[str]:
    """Human checklist printed after daemon start (and optional plugin wait)."""
    ide = probe.resolved_autopilot_ide
    sock = probe.socket_path
    settings_hint = (
        "~/.config/Cursor/User/settings.json"
        if ide == "cursor"
        else "~/.config/Code/User/settings.json"
        if ide == "vscode"
        else "IDE user settings (koruAutopilot.*)"
    )
    lines: list[str] = [
        "",
        "koru autonomous: --- co zrobić teraz (operator IDE) ---",
    ]
    if plugin_connected is True:
        lines.append(
            f"koru autonomous: [ok] plugin połączony (ide={ide}) — "
            "prompty idą do czatu, nie ydotool",
        )
    elif plugin_connected is False:
        lines.append(
            f"koru autonomous: [!] brak pluginu na {sock} — drive może użyć klawiatury "
            "(zły fokus). Napraw zanim zostawisz długi run.",
        )
    else:
        lines.append(
            "koru autonomous: [?] czekam na plugin — jeśli poniżej nie ma [ok], wykonaj kroki 1–6",
        )

    if ide == "cursor" and probe.autopilot_ide_cli == "vscode":
        lines.append(
            "koru autonomous: [!] CLI --autopilot-ide=vscode przy pracy w Cursorze — "
            "użyj IDE=cursor / --autopilot-ide cursor",
        )
    if probe.terminal_lane == "vscode" and ide == "cursor":
        lines.append(
            "koru autonomous: [!] TERM_PROGRAM=vscode w terminalu Cursora — "
            "jawnie ustaw --agent-lane cursor jeśli auto myli VS Code",
        )

    lines.extend(
        [
            f"koru autonomous: 1) Otwórz {ide} z root = {probe.project}",
            "koru autonomous: 2) MCP: włącz serwer „koru” (po Reload po task koru:mcp:bootstrap)",
            "koru autonomous: 3) Autopilot: Command Palette → „koru: Connect autopilot daemon” "
            "(pasek: koru: on)",
            f"koru autonomous: 4) Socket wtyczki = {sock} "
            f"({settings_hint}: koruAutopilot.socketPath)",
            f"koru autonomous: 5) Ten sam socket w shellu: export KORU_AUTOPILOT_INSTANCE={ide}",
            f"koru autonomous: 6) Test: koru autopilot status → plugins "
            f"niepuste; potem koru autopilot drive --ide {ide} --require-plugin 'probe test'",
            "koru autonomous: 7) (opcjonalnie) Command Palette → "
            "„koru: Calibrate chat probe ladder”",
            "koru autonomous: 8) Dashboard: task koru:server → http://localhost:8765/",
            "koru autonomous: --- docs: <project>/docs/autonomy-ide-cursor.md "
            "(sekcja „Po starcie”) ---",
        ],
    )
    return lines


__all__ = [
    "AutonomousStartupProbe",
    "build_startup_probe",
    "format_post_startup_operator_hints",
    "format_startup_banner",
    "koru_distribution_version",
    "resolve_agent_lane_id",
    "resolve_autopilot_ide_for_autonomous",
]
