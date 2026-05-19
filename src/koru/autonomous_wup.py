"""WUP ``wup watch`` subprocess and health helpers for ``koru autonomous``."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .topology import is_component_enabled, is_pipeline_enabled


def _wup_stdio_info(msg: str, *, fmt: str) -> None:
    print(msg, file=sys.stderr if fmt == "jsonl" else sys.stdout)


def _wup_topology_gate(project: Path, key: str, *, fallback: bool, enabled: bool) -> bool:
    if not enabled:
        return fallback
    try:
        if key in {
            "idle-diagnostics",
            "autoloop:queue",
            "scan:on-change",
            "autopilot:drive",
            "gate:wup",
        }:
            return is_pipeline_enabled(project, key)
        return is_component_enabled(project, key)
    except Exception:
        return fallback


@dataclass(frozen=True)
class WupWatchConfig:
    enabled: bool | None
    mode: str
    project: Path
    deps_file: str
    scenarios_dir: str
    testql_bin: str
    track_dir: str
    debounce: int
    cooldown: int
    cpu_throttle: float
    quick_limit: int
    config: Path | None


@dataclass(frozen=True)
class WupHealthResult:
    status: str
    failing_services: list[str]
    new_events: int


class _WupEventState(Protocol):
    wup_seen_events: int


def _build_wup_watch_config(args: argparse.Namespace, project: Path) -> WupWatchConfig:
    return WupWatchConfig(
        enabled=args.wup_watch,
        mode=args.wup_mode,
        project=project,
        deps_file=args.wup_deps,
        scenarios_dir=args.wup_scenarios_dir,
        testql_bin=args.wup_testql_bin,
        track_dir=args.wup_track_dir,
        debounce=args.wup_debounce,
        cooldown=args.wup_cooldown,
        cpu_throttle=args.wup_cpu_throttle,
        quick_limit=args.wup_quick_limit,
        config=args.wup_config,
    )


def _resolve_wup_testql_bin(config: WupWatchConfig) -> str:
    if config.testql_bin != "testql":
        return config.testql_bin
    project_wrapper = config.project / "scripts" / "koru-wup-testql"
    if project_wrapper.is_file():
        return str(project_wrapper)
    installed_wrapper = shutil.which("koru-wup-testql")
    if installed_wrapper is not None:
        return installed_wrapper
    return config.testql_bin


def _wup_cpu_throttle_arg(value: float) -> str:
    if value > 1:
        value = value / 100
    return str(value)


def _wup_watch_command(config: WupWatchConfig) -> list[str]:
    command = [
        "wup",
        "watch",
        str(config.project),
        "--deps",
        config.deps_file,
        "--cpu-throttle",
        _wup_cpu_throttle_arg(config.cpu_throttle),
        "--debounce",
        str(config.debounce),
        "--cooldown",
        str(config.cooldown),
        "--mode",
        config.mode,
    ]
    if config.mode == "testql":
        command.extend(
            [
                "--scenarios-dir",
                config.scenarios_dir,
                "--testql-bin",
                _resolve_wup_testql_bin(config),
                "--track-dir",
                config.track_dir,
                "--quick-limit",
                str(config.quick_limit),
            ]
        )
    if config.config is not None:
        command.extend(["--config", str(config.config)])
    return command


def _wup_autodetect(config: WupWatchConfig) -> bool:
    """Return True when wup binary and wup.yaml are both present."""
    return shutil.which("wup") is not None and (
        (config.project / "wup.yaml").is_file() or config.config is not None
    )


def _start_wup_watch(
    config: WupWatchConfig, *, topology_integration: bool, stdio_format: str = "human"
) -> subprocess.Popen | None:
    auto = config.enabled is None
    if config.enabled is False:
        return None
    wup_available = shutil.which("wup") is not None
    wup_yaml_present = (config.project / "wup.yaml").is_file() or config.config is not None
    if auto:
        if not wup_available or not wup_yaml_present:
            return None
        _wup_stdio_info(
            "koru autonomous: WUP auto-detected (wup.yaml + wup binary present)", fmt=stdio_format
        )
    else:
        if not wup_available:
            _wup_stdio_info(
                "koru autonomous: WUP watch requested but `wup` is not in PATH", fmt=stdio_format
            )
            return None
        if not wup_yaml_present:
            _wup_stdio_info(
                "koru autonomous: WUP watch requested but no wup.yaml found", fmt=stdio_format
            )
            return None
    if not _wup_topology_gate(
        config.project, "gate:wup", fallback=True, enabled=topology_integration
    ):
        _wup_stdio_info("koru autonomous: WUP watch disabled in topology", fmt=stdio_format)
        return None
    command = _wup_watch_command(config)
    _wup_stdio_info("+ " + " ".join(command), fmt=stdio_format)
    process = subprocess.Popen(command, cwd=config.project)
    _wup_stdio_info(
        f"koru autonomous: started WUP watcher pid={process.pid} mode={config.mode}",
        fmt=stdio_format,
    )
    return process


def _stop_process(
    process: subprocess.Popen | None, label: str, *, stdio_format: str = "human"
) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    _wup_stdio_info(f"koru autonomous: stopped {label}", fmt=stdio_format)


def _load_wup_health(health_path: Path) -> dict[str, dict]:
    """Load WUP health data from JSON file."""
    health: dict[str, dict] = {}
    if health_path.is_file():
        try:
            payload = json.loads(health_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                health = {str(k): v for k, v in payload.items() if isinstance(v, dict)}
        except (OSError, json.JSONDecodeError):
            health = {}
    return health


def _identify_failing_services(health: dict[str, dict]) -> list[str]:
    """Identify services with failing status."""
    return [
        service
        for service, data in sorted(health.items())
        if str(data.get("status", "")).lower() in {"down", "failed", "failure", "error"}
    ]


def _create_wup_diagnostic_tickets(
    health: dict[str, dict],
    failing: list[str],
    project: Path,
    ticket_queue: str,
    state_dir: Path,
    create_diagnostic_ticket: Callable[..., None],
) -> None:
    """Create diagnostic tickets for failing WUP services."""
    for service, data in sorted(health.items()):
        check_id = f"wup-{service}"
        if service in failing:
            stage = str(data.get("stage") or "wup")
            message = str(data.get("message") or "WUP reported failing service")
            track_file = str(data.get("track_file") or "")
            create_diagnostic_ticket(
                project=project,
                check_id=check_id,
                summary=f"WUP service={service} stage={stage} message={message} track={track_file}",
                cycle=0,
                queue_status="wup_failure",
                queue_name=ticket_queue,
                priority="high",
                state_dir=state_dir,
            )
        else:
            (state_dir / f"{check_id}.failed").unlink(missing_ok=True)


def _count_wup_events(events_path: Path, previous_count: int) -> tuple[int, int]:
    """Count WUP events and return (total_count, new_events)."""
    event_count = 0
    if events_path.is_file():
        try:
            with events_path.open("r", encoding="utf-8") as handle:
                event_count = sum(1 for line in handle if line.strip())
        except OSError:
            event_count = previous_count
    new_events = max(0, event_count - previous_count)
    return event_count, new_events


def _read_wup_health(
    *,
    project: Path,
    state: _WupEventState,
    diagnostic_tickets: bool,
    ticket_queue: str,
    state_dir: Path,
    create_diagnostic_ticket: Callable[..., None] | None,
) -> WupHealthResult:
    health_path = project / ".wup" / "service-health.json"
    events_path = project / ".wup" / "service-health-events.jsonl"
    
    health = _load_wup_health(health_path)
    failing = _identify_failing_services(health)
    
    if diagnostic_tickets:
        if failing and create_diagnostic_ticket is None:
            raise TypeError("create_diagnostic_ticket is required when diagnostic_tickets is True")
        if create_diagnostic_ticket is not None:
            _create_wup_diagnostic_tickets(
                health, failing, project, ticket_queue, state_dir, create_diagnostic_ticket
            )
    
    event_count, new_events = _count_wup_events(events_path, state.wup_seen_events)
    state.wup_seen_events = max(state.wup_seen_events, event_count)
    status = "failed" if failing else ("changed" if new_events else "ok")
    return WupHealthResult(status=status, failing_services=failing, new_events=new_events)
