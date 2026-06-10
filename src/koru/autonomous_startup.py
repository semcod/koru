"""Startup IDE / environment probe for ``koru autonomous up``."""


import importlib.metadata
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from koru.autopilot import default_socket_path
from koru.ide_router import is_headless_environment, resolve_ide_route
from koruide.ide import (
    RunningIDE,
    canonical_autopilot_ide_id,
    detect_focused_ide_id,
    detect_running_ides,
    detect_terminal_host_context,
    detect_terminal_host_ide_id,
    normalize_ide_id,
    pick_target,
    supported_autopilot_ide_ids,
    supports_vscode_extension_plugin,
)

_PLUGIN_IDE_LANES = supported_autopilot_ide_ids() - {"auto"}
_AUTOPILOT_PLUGIN_LANES = ("antigravity", "cursor", "windsurf", "vscodium", "vscode")
# Lanes that have no installable autopilot plugin but often appear in env/terminal
# hints (integrated terminal inside the IDE). Auto-correct to a plugin IDE when
# one is running — see ``_resolve_lane_from_explicit`` / ``_resolve_lane_from_terminal``.
_STALE_NONPLUGIN_LANES = frozenset({"jetbrains"})


def supports_autopilot_plugin_ide(ide: str) -> bool:
    """Return ``True`` when ``ide`` has native autopilot plugin support."""
    return supports_vscode_extension_plugin(ide)


def koru_distribution_version() -> str:
    try:
        return importlib.metadata.version("koru")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _session_label() -> str:
    from gillm.focus import resolve_active_os_strategy

    strategy = resolve_active_os_strategy()
    if strategy.id == "linux-wayland":
        return "wayland"
    if strategy.id == "linux-x11":
        return "x11"
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


def _focused_agent_lane_from_desktop() -> str | None:
    """Return focused IDE lane after desktop click/focus, when detectable."""
    focused = normalize_ide_id(detect_focused_ide_id())
    if focused and focused != "auto":
        return focused
    return None


def _explicit_agent_lane_from_env() -> tuple[str | None, str]:
    explicit = normalize_ide_id(os.environ.get("KORU_AUTOPILOT_INSTANCE"))
    if explicit and explicit != "auto":
        return explicit, "env:KORU_AUTOPILOT_INSTANCE"
    return None, ""



def _resolve_lane_from_cli(raw: str) -> tuple[str | None, str] | None:
    """Resolve lane from CLI argument without project mapping."""
    if raw == "none":
        return None, "cli:none"
    if raw != "auto":
        return raw, f"cli:{raw}"
    return None


def _pick_plugin_capable_running(
    running: Sequence[RunningIDE],
) -> RunningIDE | None:
    """Best running IDE that can use the VS Code-family autopilot plugin."""
    candidates = [ide for ide in running if supports_autopilot_plugin_ide(ide.id)]
    if not candidates:
        return None
    return pick_target(candidates)


def _explicit_lane_matches_terminal(explicit: str, terminal: str) -> bool:
    """True when ``explicit`` is the same lane or a suffixed variant (``cursor-main``)."""
    if explicit == terminal:
        return True
    return explicit.startswith(f"{terminal}-")


def _resolve_lane_from_explicit(
    explicit: str | None,
    explicit_source: str,
    terminal: str | None,
    running: Sequence[RunningIDE] | None = None,
) -> tuple[str | None, str] | None:
    """Resolve lane from explicit KORU_AUTOPILOT_INSTANCE env var."""
    if not explicit:
        return None
    if (
        terminal
        and supports_autopilot_plugin_ide(terminal)
        and not _explicit_lane_matches_terminal(explicit, terminal)
        and terminal != "vscode"
        and supports_autopilot_plugin_ide(explicit)  # Only override if explicit is also a plugin IDE
    ):
        return terminal, f"terminal:over-{explicit_source}"
    # Stale ``KORU_AUTOPILOT_INSTANCE=jetbrains`` (or zed) is a common foot-gun:
    # the lane has no installable plugin, so koru falls back to raw ydotool/wtype
    # which types into whatever window has focus — usually the file editor when
    # the integrated terminal lives inside JetBrains. If a plugin-capable IDE is
    # also running (Cursor, Windsurf, …), prefer it over the explicit env —
    # unless the user is actively working from that IDE's terminal.
    # For non-plugin lanes (jetbrains/zed), always respect the explicit choice.
    if running and explicit in _STALE_NONPLUGIN_LANES:
        if terminal and _explicit_lane_matches_terminal(explicit, terminal):
            pass
        # Only override if explicit is a plugin IDE and terminal is a different plugin IDE
        elif supports_autopilot_plugin_ide(explicit) and terminal and supports_autopilot_plugin_ide(terminal) and terminal != explicit:
            picked = _pick_plugin_capable_running(running)
            if picked is not None:
                return picked.id, f"running:over-{explicit_source}:{explicit}"
    return explicit, explicit_source


def _resolve_lane_from_vscode_terminal(
    running: Sequence[RunningIDE],
    terminal: str | None,
) -> tuple[str | None, str] | None:
    """Check if VS Code terminal should be overridden by a running plugin IDE."""
    if terminal != "vscode" or not running:
        return None
    picked = pick_target(list(running))
    if picked is not None and picked.id != terminal and picked.id in _PLUGIN_IDE_LANES:
        return picked.id, f"target:over-terminal:{terminal}"
    return None


def _resolve_lane_from_terminal(
    terminal: str | None,
    running: Sequence[RunningIDE],
) -> tuple[str | None, str] | None:
    """Resolve lane from terminal hint with fallback to running IDEs."""
    if terminal in _PLUGIN_IDE_LANES and supports_autopilot_plugin_ide(terminal):
        return terminal, "terminal"
    if terminal == "jetbrains" and running:
        picked = _pick_plugin_capable_running(running)
        if picked is not None:
            return picked.id, f"terminal:prefer-{picked.id}-over-jetbrains"
    if not terminal:
        return None
    for alt in _AUTOPILOT_PLUGIN_LANES:
        if any(ide.id == alt for ide in running):
            return alt, f"terminal:prefer-{alt}-over-{terminal}"
    return None


def _resolve_lane_from_running(
    running: Sequence[RunningIDE],
) -> tuple[str | None, str] | None:
    """Resolve lane from the best detected running IDE."""
    if not running:
        return None
    picked = pick_target(list(running))
    if picked is None:
        return None
    return picked.id, f"running:{picked.label}"


def _project_lane(project: Path, lane: str | None, resolve_project_lane) -> str | None:
    if lane is None:
        return None
    return resolve_project_lane(project, lane)


def _resolve_project_lane_result(
    project: Path,
    result: tuple[str | None, str] | None,
    resolve_project_lane,
) -> tuple[str | None, str] | None:
    if not result:
        return None
    lane, source = result
    return _project_lane(project, lane, resolve_project_lane), source


def _runtime_lane_hints() -> tuple[str | None, str | None, str | None, str, Sequence[RunningIDE]]:
    focused = _focused_agent_lane_from_desktop()
    terminal = _terminal_agent_lane_from_env()
    explicit, explicit_source = _explicit_agent_lane_from_env()
    running = detect_running_ides()
    return focused, terminal, explicit, explicit_source, running


def _resolve_lane_from_runtime_hints(
    project: Path,
    *,
    focused: str | None,
    terminal: str | None,
    explicit: str | None,
    explicit_source: str,
    running: Sequence[RunningIDE],
    resolve_project_lane,
) -> tuple[str | None, str] | None:
    # In external-terminal workflows the user can pick target IDE by focusing
    # its window before running `koru auto`; treat desktop focus as the strongest
    # runtime signal for auto lane routing only when that IDE is also observed
    # in the running-IDE list. This prevents stale host desktop focus from
    # overriding isolated tests or project markers when no matching IDE process
    # was detected.
    focused_is_running = bool(focused and any(ide.id == focused for ide in running))
    if (
        focused
        and focused in _PLUGIN_IDE_LANES
        and focused_is_running
        and (
            not explicit
            or (not terminal and not _explicit_lane_matches_terminal(explicit, focused))
        )
    ):
        return _project_lane(project, focused, resolve_project_lane), "focused"

    for result in (
        _resolve_lane_from_explicit(explicit, explicit_source, terminal, running),
        _resolve_lane_from_vscode_terminal(running, terminal),
        _resolve_lane_from_terminal(terminal, running),
    ):
        resolved = _resolve_project_lane_result(project, result, resolve_project_lane)
        if resolved:
            return resolved
    return None


def _resolve_lane_from_running_or_project(
    project: Path,
    running: Sequence[RunningIDE],
    *,
    resolve_project_lane,
) -> tuple[str | None, str]:
    running_result = _resolve_lane_from_running(running)
    if running_result:
        return running_result
    return resolve_project_lane(project, "auto"), "project-markers"



def resolve_agent_lane_id(
    project: Path,
    agent_lane_cli: str,
    *,
    resolve_project_lane,
) -> tuple[str | None, str]:
    """Resolve ``--agent-lane``; return ``(lane_id, source_label)``."""
    raw = normalize_ide_id(agent_lane_cli) or "auto"

    cli_result = _resolve_project_lane_result(
        project,
        _resolve_lane_from_cli(raw),
        resolve_project_lane,
    )
    if cli_result:
        return cli_result

    focused, terminal, explicit, explicit_source, running = _runtime_lane_hints()
    runtime_result = _resolve_lane_from_runtime_hints(
        project,
        focused=focused,
        terminal=terminal,
        explicit=explicit,
        explicit_source=explicit_source,
        running=running,
        resolve_project_lane=resolve_project_lane,
    )
    if runtime_result:
        return runtime_result

    return _resolve_lane_from_running_or_project(
        project,
        running,
        resolve_project_lane=resolve_project_lane,
    )



def resolve_agent_lane(
    *,
    cli_lane: str = "auto",
    running_ides: list[RunningIDE] | tuple[RunningIDE, ...] | None = None,
    terminal_hint: str | None = None,
) -> tuple[str | None, str]:
    raw = normalize_ide_id(cli_lane) or "auto"

    cli_result = _resolve_lane_from_cli(raw)
    if cli_result:
        return cli_result

    terminal = normalize_ide_id(terminal_hint) if terminal_hint is not None else None
    if terminal is None:
        terminal = _terminal_agent_lane_from_env()
    running = list(running_ides) if running_ides is not None else detect_running_ides()
    focused = _focused_agent_lane_from_desktop()
    explicit, explicit_source = _explicit_agent_lane_from_env()

    if (
        focused
        and focused in _PLUGIN_IDE_LANES
        and any(ide.id == focused for ide in running)
        and (
            not explicit
            or (not terminal and not _explicit_lane_matches_terminal(explicit, focused))
        )
    ):
        return focused, "focused"

    explicit_result = _resolve_lane_from_explicit(explicit, explicit_source, terminal)
    if explicit_result:
        return explicit_result

    for result in (
        _resolve_lane_from_vscode_terminal(running, terminal),
        _resolve_lane_from_terminal(terminal, running),
        _resolve_lane_from_running(running),
    ):
        if result:
            return result

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
    # Respect the lane even for non-plugin IDEs (e.g., jetbrains) when explicitly set.
    # Instance slugs like windsurf-main map to canonical IDE ids (windsurf).
    if lane and lane != "auto":
        return canonical_autopilot_ide_id(lane), "lane"
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
    terminal_host_source: str = "none"
    terminal_host_kind: str = "system"
    socket_path: str = ""
    session: str = "headless"
    term_program: str = "-"
    headless: bool = False
    xdg_runtime_dir: str = "-"


@dataclass(frozen=True)
class _StartupProbeResolution:
    lane: str | None
    lane_source: str
    resolved_ide: str
    autopilot_ide_source: str


@dataclass(frozen=True)
class _StartupProbeRuntimeFields:
    running_ides: tuple[str, ...]
    terminal_lane: str | None
    terminal_host_source: str
    terminal_host_kind: str
    socket_path: str
    session: str
    term_program: str
    headless: bool
    xdg_runtime_dir: str


def _normalized_cli_value(raw: str | None) -> str:
    return (raw or "auto").strip().lower()


def _autopilot_socket_path_for_probe(ide_id: str) -> str:
    if not ide_id or ide_id == "auto":
        return str(default_socket_path())
    previous_instance = os.environ.get("KORU_AUTOPILOT_INSTANCE")
    previous_socket = os.environ.get("KORU_AUTOPILOT_SOCKET")
    try:
        os.environ["KORU_AUTOPILOT_INSTANCE"] = ide_id
        # Ignore stale koruenv socket overlays; compute the expected per-IDE path.
        os.environ.pop("KORU_AUTOPILOT_SOCKET", None)
        return str(default_socket_path())
    finally:
        if previous_instance is None:
            os.environ.pop("KORU_AUTOPILOT_INSTANCE", None)
        else:
            os.environ["KORU_AUTOPILOT_INSTANCE"] = previous_instance
        if previous_socket is None:
            os.environ.pop("KORU_AUTOPILOT_SOCKET", None)
        else:
            os.environ["KORU_AUTOPILOT_SOCKET"] = previous_socket


def _running_ide_labels() -> tuple[str, ...]:
    return tuple(f"{ide.label} (pid={ide.pid})" for ide in detect_running_ides())


def _term_program_label() -> str:
    return (os.environ.get("TERM_PROGRAM") or "").strip() or "-"


def _xdg_runtime_dir_label() -> str:
    return (os.environ.get("XDG_RUNTIME_DIR") or "").strip() or "-"


def _resolve_startup_probe_resolution(
    project: Path,
    *,
    agent_lane_cli: str,
    autopilot_ide_cli: str,
    resolve_project_lane,
    resolve_ide_route_fn,
) -> _StartupProbeResolution:
    lane, lane_source = resolve_agent_lane_id(
        project,
        agent_lane_cli,
        resolve_project_lane=resolve_project_lane,
    )
    resolved_ide, ide_source = resolve_autopilot_ide_for_autonomous(
        autopilot_ide_cli,
        lane,
        resolve_ide_route_fn=resolve_ide_route_fn,
    )
    return _StartupProbeResolution(
        lane=lane,
        lane_source=lane_source,
        resolved_ide=resolved_ide,
        autopilot_ide_source=ide_source,
    )


def _startup_probe_runtime_fields(ide_id: str) -> _StartupProbeRuntimeFields:
    terminal_ctx = detect_terminal_host_context()
    return _StartupProbeRuntimeFields(
        running_ides=_running_ide_labels(),
        terminal_lane=terminal_ctx.ide,
        terminal_host_source=terminal_ctx.source,
        terminal_host_kind=terminal_ctx.kind,
        socket_path=_autopilot_socket_path_for_probe(ide_id),
        session=_session_label(),
        term_program=_term_program_label(),
        headless=is_headless_environment(),
        xdg_runtime_dir=_xdg_runtime_dir_label(),
    )


def _build_startup_probe_from_resolution(
    project: Path,
    *,
    agent_lane_cli: str,
    autopilot_ide_cli: str,
    resolution: _StartupProbeResolution,
) -> AutonomousStartupProbe:
    instance_for_socket = resolution.lane or resolution.resolved_ide
    runtime = _startup_probe_runtime_fields(instance_for_socket)
    return AutonomousStartupProbe(
        koru_version=koru_distribution_version(),
        python_version=sys.version.split()[0],
        project=project.resolve(),
        agent_lane_cli=_normalized_cli_value(agent_lane_cli),
        autopilot_ide_cli=_normalized_cli_value(autopilot_ide_cli),
        resolved_lane=resolution.lane,
        lane_source=resolution.lane_source,
        resolved_autopilot_ide=resolution.resolved_ide,
        autopilot_ide_source=resolution.autopilot_ide_source,
        running_ides=runtime.running_ides,
        terminal_lane=runtime.terminal_lane,
        terminal_host_source=runtime.terminal_host_source,
        terminal_host_kind=runtime.terminal_host_kind,
        socket_path=runtime.socket_path,
        session=runtime.session,
        term_program=runtime.term_program,
        headless=runtime.headless,
        xdg_runtime_dir=runtime.xdg_runtime_dir,
    )


def build_startup_probe(
    project: Path,
    *,
    agent_lane_cli: str,
    autopilot_ide_cli: str,
    resolve_project_lane,
    resolve_ide_route_fn=resolve_ide_route,
) -> AutonomousStartupProbe:
    resolution = _resolve_startup_probe_resolution(
        project,
        agent_lane_cli=agent_lane_cli,
        autopilot_ide_cli=autopilot_ide_cli,
        resolve_project_lane=resolve_project_lane,
        resolve_ide_route_fn=resolve_ide_route_fn,
    )
    return _build_startup_probe_from_resolution(
        project=project.resolve(),
        agent_lane_cli=agent_lane_cli,
        autopilot_ide_cli=autopilot_ide_cli,
        resolution=resolution,
    )


def format_startup_banner(probe: AutonomousStartupProbe) -> list[str]:
    lines = [
        f"koru autonomous: koru {probe.koru_version} (python {probe.python_version})",
        f"koru autonomous: project {probe.project}",
        f"koru autonomous: session={probe.session} TERM_PROGRAM={probe.term_program} "
        f"XDG_RUNTIME_DIR={probe.xdg_runtime_dir}",
    ]
    if probe.running_ides:
        lines.append(f"koru autonomous: running IDEs: {'; '.join(probe.running_ides)}")
    else:
        lines.append("koru autonomous: running IDEs: (none detected)")
    if probe.terminal_lane:
        lines.append(
            "koru autonomous: terminal hint → "
            f"{probe.terminal_lane} "
            f"(kind={probe.terminal_host_kind}, source={probe.terminal_host_source})"
        )
        if probe.terminal_host_kind == "ide_adjacent":
            lines.append(
                "koru autonomous: terminal note → external/system shell with IDE ancestor; "
                "prefer the target IDE integrated terminal for reliable lane alignment"
            )
    else:
        lines.append(
            "koru autonomous: terminal hint → none "
            f"(kind={probe.terminal_host_kind}, source={probe.terminal_host_source})"
        )
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
    if ide == "antigravity":
        return "~/.config/Antigravity/User/settings.json"
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
    plugin_blocker: str | None = None,
    plugin_reason: str | None = None,
) -> str:
    """Format plugin connection status line."""
    if plugin_supported and plugin_connected is True:
        return (
            f"koru autonomous: [ok] plugin połączony (ide={ide}) — "
            f"prompty idą do czatu, nie ydotool"
        )
    if plugin_supported and plugin_connected is False:
        blocker = (plugin_blocker or "plugin_not_connected").strip()
        reason = (plugin_reason or "").strip()
        if blocker == "plugin_version_mismatch":
            tail = (
                "wersja/protokół aktywnej wtyczki nie pasuje do daemona. "
                "Zrób Developer: Reload Window po instalacji aktualnego VSIX, "
                "potem połącz plugin."
            )
        elif blocker == "plugin_status_unavailable":
            tail = (
                "daemon nie zwraca statusu pluginu. Sprawdź socket i uruchom "
                "`koru autopilot status --explain`."
            )
        else:
            tail = (
                "plugin nie jest połączony z daemonem. Jeśli VSIX był instalowany "
                "po starcie IDE, zrób Developer: Reload Window albo restart IDE, "
                "potem połącz plugin."
            )
        reason_part = f" Powód: {reason}." if reason else ""
        return (
            f"koru autonomous: [!] brak zgodnego pluginu ({blocker}) na {sock} — "
            f"drive jest wstrzymany w trybie strict; {tail}{reason_part}"
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
    if ide != "jetbrains" and "jetbrains" in running_labels:
        lines.append(
            "koru autonomous: [!] JetBrains IDE działa, ale autopilot wybrał "
            f"ide={ide}; Koru nie będzie sterował oknem chatu JetBrains. "
            "Jeśli chcesz JetBrains, uruchom z --agent-lane jetbrains "
            "--autopilot-ide jetbrains albo ustaw KORU_AUTOPILOT_INSTANCE=jetbrains. "
            "Uwaga: JetBrains używa ścieżki keyboard/OS-injector, nie VSIX pluginu."
        )

    return lines


def _format_plugin_setup_steps(
    ide: str,
    sock: str,
    settings_hint: str,
    project: Path,
    *,
    lane: str | None = None,
) -> list[str]:
    """Format setup steps for plugin-based IDEs."""
    instance = (lane or ide).strip()
    return [
        f"koru autonomous: 1) Otwórz {ide} z root = {project}",
        "koru autonomous: 2) MCP: włącz serwer „koru” "
        "(po Reload po task koru:mcp:bootstrap)",
        "koru autonomous: 3) Autopilot: Command Palette → „koru: Connect autopilot daemon” "
        "(pasek: koru: on)",
        "koru autonomous:    Jeśli komendy nie ma albo plugin list jest pusty po instalacji VSIX: "
        "Developer: Reload Window / restart IDE",
        f"koru autonomous: 4) Socket wtyczki = {sock} "
        f"({settings_hint}: koruAutopilot.socketPath)",
        "koru autonomous: 5) Ten sam socket w shellu: export "
        f"KORU_AUTOPILOT_INSTANCE={instance}",
        f"koru autonomous: 6) Diagnostyka mostu: koru ide doctor --ide {ide} --fix",
        f"koru autonomous: 7) Test: koru autopilot status --ide {ide} --explain "
        "→ plugins niepuste; "
        f"potem koru autopilot drive --ide {ide} --require-plugin 'probe test'",
        f"koru autonomous: 7a) Przed drive: kliknij w pole czatu {ide} "
        "(mrugający kursor w input, nie w edytorze pliku)",
        "koru autonomous: 8) (opcjonalnie) Command Palette → "
        "„koru: Calibrate chat probe ladder” "
        "(po ustawieniu fokusu w polu czatu; submit na Wayland)",
        "koru autonomous: 9) Dashboard: task koru:server → http://localhost:8765/",
        "koru autonomous: --- docs: <project>/docs/autonomy-ide-cursor.md "
        "(sekcja „Po starcie”) ---",
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
        "koru autonomous:    Na Waylandzie włącz fallback jawnie: export KORU_OS_INJECTOR=1; "
        "kliknij/skalibruj pole chatu przed testem.",
        f"koru autonomous: 6) Test: koru autopilot drive --ide {ide} 'probe test' "
        "(fallback keyboard/OS-injector)",
        "koru autonomous: 7) Dashboard: task koru:server → http://localhost:8765/",
    ]


def format_post_startup_operator_hints(
    probe: AutonomousStartupProbe,
    *,
    plugin_connected: bool | None = None,
    plugin_blocker: str | None = None,
    plugin_reason: str | None = None,
    compact: bool = False,
) -> list[str]:
    """Human checklist printed after daemon start (and optional plugin wait)."""
    ide = probe.resolved_autopilot_ide
    sock = probe.socket_path
    settings_hint = _get_settings_hint(ide)
    plugin_supported = supports_autopilot_plugin_ide(ide)
    status_line = _format_plugin_status_line(
        ide,
        plugin_supported,
        plugin_connected,
        sock,
        plugin_blocker=plugin_blocker,
        plugin_reason=plugin_reason,
    )
    mismatch_warnings = _format_ide_mismatch_warnings(probe)

    if compact and plugin_supported and plugin_connected is False:
        return [
            status_line,
            *mismatch_warnings,
            "koru autonomous: next reload/reconnect plugin; "
            "check: koru autopilot status --explain; "
            f"repair: koru ide doctor --ide {ide} --fix --explain",
        ]

    lines: list[str] = [
        "",
        "koru autonomous: --- co zrobić teraz (operator IDE) ---",
    ]

    lines.append(status_line)
    lines.extend(mismatch_warnings)

    if plugin_supported:
        lines.extend(
            _format_plugin_setup_steps(
                ide,
                sock,
                settings_hint,
                probe.project,
                lane=probe.resolved_lane,
            )
        )
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
    "canonical_autopilot_ide_id",
    "resolve_agent_lane",
    "resolve_agent_lane_id",
    "resolve_autopilot_ide_for_autonomous",
    "supports_autopilot_plugin_ide",
]
