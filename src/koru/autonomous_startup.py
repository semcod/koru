"""Startup IDE / environment probe for ``koru autonomous up``."""


import importlib.metadata
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from koru.autopilot import default_socket_path
from koruide.ide import (
    RunningIDE,
    detect_running_ides,
    detect_terminal_host_ide_id,
    normalize_ide_id,
    pick_target,
    supported_autopilot_ide_ids,
    supports_vscode_extension_plugin,
)
from koru.ide_router import is_headless_environment, resolve_ide_route

_PLUGIN_IDE_LANES = supported_autopilot_ide_ids() - {"auto"}
_AUTOPILOT_PLUGIN_LANES = ("cursor", "windsurf", "vscodium", "vscode")


def supports_autopilot_plugin_ide(ide: str) -> bool:
    """Return ``True`` when ``ide`` has native autopilot plugin support."""
    return supports_vscode_extension_plugin(ide)


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
    host = normalize_ide_id(detect_terminal_host_ide_id())
    if host:
        return host
    explicit = normalize_ide_id(os.environ.get("KORU_AUTOPILOT_IDE"))
    if explicit and explicit != "auto":
        return explicit
    return None


def _explicit_agent_lane_from_env() -> tuple[str | None, str]:
    explicit = normalize_ide_id(os.environ.get("KORU_AUTOPILOT_INSTANCE"))
    if explicit and explicit != "auto":
        return explicit, "env:KORU_AUTOPILOT_INSTANCE"
    return None, ""


def _target_lane_over_terminal(terminal: str | None) -> tuple[str | None, str]:
    if terminal != "vscode":
        return None, ""
    running = detect_running_ides()
    if not running:
        return None, ""
    picked = pick_target(running)
    if picked is None or picked.id == terminal or picked.id not in _PLUGIN_IDE_LANES:
        return None, ""
    return picked.id, f"target:over-terminal:{terminal}"


def _resolve_lane_from_cli(
    project: Path,
    raw: str,
    resolve_project_lane,
) -> tuple[str | None, str] | None:
    """Resolve lane from CLI argument."""
    if raw == "none":
        return None, "cli:none"
    if raw != "auto":
        lane = resolve_project_lane(project, raw)
        return lane, f"cli:{raw}"
    return None


def _resolve_lane_with_explicit(
    project: Path,
    terminal: str | None,
    explicit: str | None,
    explicit_source: str,
    resolve_project_lane,
) -> tuple[str | None, str] | None:
    """Resolve lane when explicit instance is set."""
    if not explicit:
        return None
    if terminal in _PLUGIN_IDE_LANES and terminal != explicit and terminal != "vscode":
        lane = resolve_project_lane(project, terminal)
        return lane, f"terminal:over-{explicit_source}"
    lane = resolve_project_lane(project, explicit)
    return lane, explicit_source


def _resolve_lane_from_running_ide_fallback(
    project: Path,
    terminal: str | None,
    resolve_project_lane,
) -> tuple[str | None, str] | None:
    """Resolve lane by checking running IDEs for plugin support."""
    if not terminal:
        return None
    running = detect_running_ides()
    for alt in _AUTOPILOT_PLUGIN_LANES:
        if any(ide.id == alt for ide in running):
            lane = resolve_project_lane(project, alt)
            return lane, f"terminal:prefer-{alt}-over-{terminal}"
    return None


def resolve_agent_lane_id(
    project: Path,
    agent_lane_cli: str,
    *,
    resolve_project_lane,
) -> tuple[str | None, str]:
    """Resolve ``--agent-lane``; return ``(lane_id, source_label)``."""
    raw = normalize_ide_id(agent_lane_cli) or "auto"
    
    cli_result = _resolve_lane_from_cli(project, raw, resolve_project_lane)
    if cli_result:
        return cli_result

    terminal = _terminal_agent_lane_from_env()
    explicit, explicit_source = _explicit_agent_lane_from_env()
    
    explicit_result = _resolve_lane_with_explicit(
        project, terminal, explicit, explicit_source, resolve_project_lane
    )
    if explicit_result:
        return explicit_result

    target, target_source = _target_lane_over_terminal(terminal)
    if target:
        lane = resolve_project_lane(project, target)
        return lane, target_source

    if terminal in _PLUGIN_IDE_LANES:
        lane = resolve_project_lane(project, terminal)
        return lane, "terminal"
    
    running_fallback = _resolve_lane_from_running_ide_fallback(project, terminal, resolve_project_lane)
    if running_fallback:
        return running_fallback

    running = detect_running_ides()
    if running:
        picked = pick_target(running)
        if picked is not None:
            return picked.id, f"running:{picked.label}"

    marker = resolve_project_lane(project, "auto")
    return marker, "project-markers"


def _resolve_lane_from_explicit(
    explicit: str | None,
    explicit_source: str,
    terminal: str | None,
) -> tuple[str | None, str] | None:
    """Resolve lane from explicit KORU_AUTOPILOT_INSTANCE env var."""
    if not explicit:
        return None
    if terminal in _PLUGIN_IDE_LANES and terminal != explicit and terminal != "vscode":
        return terminal, f"terminal:over-{explicit_source}"
    return explicit, explicit_source


def _resolve_lane_from_vscode_terminal(
    running: list[RunningIDE],
    terminal: str | None,
) -> tuple[str | None, str] | None:
    """Check if VSCode terminal should be overridden by a running plugin IDE."""
    if terminal != "vscode" or not running:
        return None
    picked = pick_target(running)
    if picked is not None and picked.id != terminal and picked.id in _PLUGIN_IDE_LANES:
        return picked.id, f"target:over-terminal:{terminal}"
    return None


def _resolve_lane_from_terminal(
    terminal: str | None,
    running: list[RunningIDE],
) -> tuple[str | None, str] | None:
    """Resolve lane from terminal hint with fallback to running IDEs."""
    if terminal in _PLUGIN_IDE_LANES:
        return terminal, "terminal"
    if not terminal:
        return None
    for alt in _AUTOPILOT_PLUGIN_LANES:
        if any(ide.id == alt for ide in running):
            return alt, f"terminal:prefer-{alt}-over-{terminal}"
    return None


def resolve_agent_lane(
    *,
    cli_lane: str = "auto",
    running_ides: list[RunningIDE] | tuple[RunningIDE, ...] | None = None,
    terminal_hint: str | None = None,
) -> tuple[str | None, str]:
    raw = normalize_ide_id(cli_lane) or "auto"
    if raw == "none":
        return None, "cli:none"
    if raw != "auto":
        return raw, f"cli:{raw}"

    terminal = normalize_ide_id(terminal_hint) if terminal_hint is not None else None
    if terminal is None:
        terminal = _terminal_agent_lane_from_env()
    
    explicit, explicit_source = _explicit_agent_lane_from_env()
    explicit_result = _resolve_lane_from_explicit(explicit, explicit_source, terminal)
    if explicit_result:
        return explicit_result

    running = list(running_ides) if running_ides is not None else detect_running_ides()
    
    vscode_result = _resolve_lane_from_vscode_terminal(running, terminal)
    if vscode_result:
        return vscode_result
    
    terminal_result = _resolve_lane_from_terminal(terminal, running)
    if terminal_result:
        return terminal_result
    
    if running:
        picked = pick_target(running)
        if picked is not None:
            return picked.id, f"running:{picked.label}"
    return "auto", "project-markers"


def resolve_autopilot_ide_for_autonomous(
    autopilot_ide_cli: str,
    lane: str | None,
    *,
    resolve_ide_route_fn,
    detect_running_ides_fn=detect_running_ides,
) -> tuple[str, str]:
    """Return ``(autopilot_ide, source_label)`` aligned with the resolved lane."""
    raw = normalize_ide_id(autopilot_ide_cli) or "auto"
    if raw != "auto":
        route = resolve_ide_route_fn(cli_autopilot_ide=raw)
        return route.autopilot_ide, f"cli:{raw}"
    if lane and lane in _PLUGIN_IDE_LANES:
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


def _normalized_cli_value(raw: str | None) -> str:
    return (raw or "auto").strip().lower()


def _autopilot_socket_path_for_probe(autopilot_ide: str) -> str:
    if not _should_probe_per_ide_socket(autopilot_ide):
        return str(default_socket_path())
    previous_instance = os.environ.get("KORU_AUTOPILOT_INSTANCE")
    try:
        os.environ["KORU_AUTOPILOT_INSTANCE"] = autopilot_ide
        return str(default_socket_path())
    finally:
        if previous_instance is None:
            os.environ.pop("KORU_AUTOPILOT_INSTANCE", None)
        else:
            os.environ["KORU_AUTOPILOT_INSTANCE"] = previous_instance


def _should_probe_per_ide_socket(autopilot_ide: str) -> bool:
    return (
        bool(autopilot_ide)
        and autopilot_ide != "auto"
        and not (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip()
        and not (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip()
    )


def _running_ide_labels() -> tuple[str, ...]:
    return tuple(f"{ide.label} (pid={ide.pid})" for ide in detect_running_ides())


def _term_program_label() -> str:
    return (os.environ.get("TERM_PROGRAM") or "").strip() or "-"


def _xdg_runtime_dir_label() -> str:
    return (os.environ.get("XDG_RUNTIME_DIR") or "").strip() or "-"


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
    return AutonomousStartupProbe(
        koru_version=koru_distribution_version(),
        python_version=sys.version.split()[0],
        project=project.resolve(),
        agent_lane_cli=_normalized_cli_value(agent_lane_cli),
        autopilot_ide_cli=_normalized_cli_value(autopilot_ide_cli),
        resolved_lane=lane,
        lane_source=lane_source,
        resolved_autopilot_ide=autopilot_ide,
        autopilot_ide_source=ide_source,
        running_ides=_running_ide_labels(),
        terminal_lane=_terminal_agent_lane_from_env(),
        socket_path=_autopilot_socket_path_for_probe(autopilot_ide),
        session=_session_label(),
        term_program=_term_program_label(),
        headless=is_headless_environment(),
        xdg_runtime_dir=_xdg_runtime_dir_label(),
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


def _get_settings_hint(ide: str) -> str:
    """Return settings file path for the given IDE."""
    if ide == "cursor":
        return "~/.config/Cursor/User/settings.json"
    if ide == "vscode":
        return "~/.config/Code/User/settings.json"
    if ide == "vscodium":
        return "~/.config/VSCodium/User/settings.json"
    return "IDE user settings (koruAutopilot.*)"


def _format_plugin_status_line(
    ide: str,
    plugin_supported: bool,
    plugin_connected: bool | None,
    sock: str,
) -> str:
    """Format plugin connection status line."""
    if plugin_supported and plugin_connected is True:
        return (
            f"koru autonomous: [ok] plugin połączony (ide={ide}) — "
            f"prompty idą do czatu, nie ydotool"
        )
    if plugin_supported and plugin_connected is False:
        return (
            f"koru autonomous: [!] brak zgodnego pluginu na {sock} — "
            f"drive jest wstrzymany w trybie strict. Reload IDE, potem połącz plugin."
        )
    if not plugin_supported:
        return (
            f"koru autonomous: [i] plugin niedostępny dla ide={ide} — "
            f"używam ścieżki keyboard/OS-injector"
        )
    return (
        "koru autonomous: [?] czekam na plugin — jeśli poniżej nie ma [ok], wykonaj kroki 1–6"
    )


def _format_ide_mismatch_warnings(probe: AutonomousStartupProbe) -> list[str]:
    """Format warnings about IDE/CLI mismatches."""
    ide = probe.resolved_autopilot_ide
    lines: list[str] = []
    
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
    
    running_labels = " ".join(probe.running_ides).lower()
    if ide == "vscode" and "vscodium" in running_labels:
        lines.append(
            "koru autonomous: [!] wybrano ide=vscode, ale działa też VSCodium — "
            "to osobne lane/sockety; jeśli pracujesz w VSCodium, uruchom z "
            "--agent-lane vscodium --autopilot-ide vscodium",
        )
    if probe.terminal_lane == "vscodium" and ide == "vscode":
        lines.append(
            "koru autonomous: [!] terminal wygląda na VSCodium, ale autopilot wybrał vscode — "
            "ustaw KORU_AUTOPILOT_INSTANCE=vscodium albo użyj --autopilot-ide vscodium",
        )
    
    return lines


def _format_plugin_setup_steps(
    ide: str,
    sock: str,
    settings_hint: str,
    project: Path,
) -> list[str]:
    """Format setup steps for plugin-based IDEs."""
    return [
        f"koru autonomous: 1) Otwórz {ide} z root = {project}",
        "koru autonomous: 2) MCP: włącz serwer „koru” "
        "(po Reload po task koru:mcp:bootstrap)",
        "koru autonomous: 3) Autopilot: Command Palette → „koru: Connect autopilot daemon” "
        "(pasek: koru: on)",
        f"koru autonomous: 4) Socket wtyczki = {sock} "
        f"({settings_hint}: koruAutopilot.socketPath)",
        "koru autonomous: 5) Ten sam socket w shellu: export "
        f"KORU_AUTOPILOT_INSTANCE={ide}",
        f"koru autonomous: 6) Test: koru autopilot status → plugins "
        f"niepuste; potem koru autopilot drive --ide {ide} --require-plugin 'probe test'",
        "koru autonomous: 7) (opcjonalnie) Command Palette → "
        "„koru: Calibrate chat probe ladder”",
        "koru autonomous: 8) Dashboard: task koru:server → http://localhost:8765/",
        "koru autonomous: --- docs: <project>/docs/autonomy-ide-cursor.md "
        "(sekcja „Po starcie\") ---",
    ]


def _format_keyboard_setup_steps(
    ide: str,
    sock: str,
    project: Path,
) -> list[str]:
    """Format setup steps for keyboard/OS-injector based IDEs."""
    return [
        f"koru autonomous: 1) Otwórz {ide} z root = {project}",
        "koru autonomous: 2) MCP: włącz serwer „koru” "
        "(po Reload po task koru:mcp:bootstrap)",
        f"koru autonomous: 3) Socket daemona = {sock}",
        f"koru autonomous: 4) Ustaw w shellu: export KORU_AUTOPILOT_INSTANCE={ide}",
        f"koru autonomous: 5) Skalibruj OS injector: task koru:ide-os:calibrate IDE={ide}",
        f"koru autonomous: 6) Test: koru autopilot drive --ide {ide} 'probe test' "
        "(fallback keyboard/OS-injector)",
        "koru autonomous: 7) Dashboard: task koru:server → http://localhost:8765/",
    ]


def format_post_startup_operator_hints(
    probe: AutonomousStartupProbe,
    *,
    plugin_connected: bool | None = None,
) -> list[str]:
    """Human checklist printed after daemon start (and optional plugin wait)."""
    ide = probe.resolved_autopilot_ide
    sock = probe.socket_path
    settings_hint = _get_settings_hint(ide)
    
    lines: list[str] = [
        "",
        "koru autonomous: --- co zrobić teraz (operator IDE) ---",
    ]
    
    plugin_supported = supports_autopilot_plugin_ide(ide)
    lines.append(_format_plugin_status_line(ide, plugin_supported, plugin_connected, sock))
    lines.extend(_format_ide_mismatch_warnings(probe))
    
    if plugin_supported:
        lines.extend(_format_plugin_setup_steps(ide, sock, settings_hint, probe.project))
    else:
        lines.extend(_format_keyboard_setup_steps(ide, sock, probe.project))
    
    return lines


__all__ = [
    "AutonomousStartupProbe",
    "RunningIDE",
    "build_startup_probe",
    "format_post_startup_operator_hints",
    "format_startup_banner",
    "koru_distribution_version",
    "resolve_agent_lane",
    "resolve_agent_lane_id",
    "resolve_autopilot_ide_for_autonomous",
    "supports_autopilot_plugin_ide",
]
