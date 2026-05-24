"""WUP ``wup watch`` subprocess and health helpers for ``koru autonomous``."""


import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import yaml

from koru.autonomous_diag_markers import diagnostic_marker_path
from koru.topology import is_component_enabled, is_pipeline_enabled


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


_FAIL_STATUSES = {"down", "failed", "failure", "error"}
_INTERRUPTED_MARKERS = (
    "aborted",
    "interrupted",
    "ctrl+c",
    "cancelled",
    "canceled",
    "sigterm",
)


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
    project_venv_wrapper = config.project / ".venv" / "bin" / "koru-wup-testql"
    if project_venv_wrapper.is_file():
        return str(project_venv_wrapper)
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
            ],
        )
    if config.config is not None:
        command.extend(["--config", str(config.config)])
    return command


def _wup_autodetect(config: WupWatchConfig) -> bool:
    """Return True when wup binary and wup.yaml are both present."""
    return shutil.which("wup") is not None and (
        (config.project / "wup.yaml").is_file() or config.config is not None
    )


def _wup_config_path(config: WupWatchConfig) -> Path:
    return config.config if config.config is not None else config.project / "wup.yaml"


def _load_project_env(project: Path) -> dict[str, str]:
    """Load .wup.env and .env into a child-process environment without overwriting current vars."""
    env = dict(os.environ)
    for env_name in (".wup.env", ".env"):
        env_path = project / env_name
        if not env_path.is_file():
            continue
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in env:
                env[key] = value
    return env


def _wup_subprocess_env(config: WupWatchConfig) -> dict[str, str]:
    env = _load_project_env(config.project)
    browsers_path = env.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if not browsers_path:
        local_browsers = config.project / ".playwright-browsers"
        if local_browsers.exists():
            env["PLAYWRIGHT_BROWSERS_PATH"] = str(local_browsers)
    return env


def _parse_wup_services(config: WupWatchConfig) -> dict | None:
    """Load and parse WUP YAML, returning the services dict or None."""
    path = _wup_config_path(config)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(raw, dict):
        return None
    services = raw.get("monitoring", {}).get("wup_services", {})
    return services if isinstance(services, dict) else None


def _extract_docker_items(service: dict) -> list[tuple[str, tuple[str, ...], str]]:
    """Extract compose service items from one WUP service entry."""
    items: list[tuple[str, tuple[str, ...], str]] = []
    for docker in service.get("docker", []) or []:
        if not isinstance(docker, dict):
            continue
        compose_service = str(docker.get("compose_service") or "").strip()
        compose_file = str(docker.get("compose_file") or "docker-compose.yml").strip()
        profiles = tuple(str(p).strip() for p in docker.get("profiles", []) or [] if str(p).strip())
        if compose_service and compose_file and profiles:
            items.append((compose_file, profiles, compose_service))
    return items


def _profiled_compose_services(config: WupWatchConfig) -> list[tuple[str, tuple[str, ...], str]]:
    """Return compose services that require opt-in profiles from the WUP manifest."""
    services = _parse_wup_services(config)
    if services is None:
        return []

    needed: list[tuple[str, tuple[str, ...], str]] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    for service in services.values():
        if not isinstance(service, dict):
            continue
        for item in _extract_docker_items(service):
            if item not in seen:
                seen.add(item)
                needed.append(item)
    return needed


def _compose_ps_command(
    compose_file: str,
    profiles: tuple[str, ...],
    compose_service: str,
) -> list[str]:
    command = ["docker", "compose", "-f", compose_file]
    for profile in profiles:
        command.extend(["--profile", profile])
    command.extend(["ps", "--format", "json", compose_service])
    return command


def _parse_compose_ps_json(raw: str) -> list[dict]:
    raw = raw.strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        items: list[dict] = []
        for line in raw.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                items.append(item)
        return items
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _compose_field(item: dict, primary: str, fallback: str) -> str:
    return str(item.get(primary) or item.get(fallback) or "").lower()


def _compose_health_ready(health: str) -> bool:
    return not health or health in {"healthy", "none"}


def _compose_state_ready(state: str) -> bool:
    return not state or state == "running"


def _compose_status_ready(state: str, status: str) -> bool:
    if state:
        return True
    return "up" in status


def _compose_service_item_ready(item: dict) -> bool:
    state = _compose_field(item, "State", "state")
    health = _compose_field(item, "Health", "health")
    status = _compose_field(item, "Status", "status")
    return (
        _compose_health_ready(health)
        and _compose_state_ready(state)
        and _compose_status_ready(state, status)
    )


def _compose_service_ready(items: list[dict]) -> bool:
    if not items:
        return False
    return all(_compose_service_item_ready(item) for item in items)


def _wait_for_compose_service_ready(
    config: WupWatchConfig,
    compose_file: str,
    profiles: tuple[str, ...],
    compose_service: str,
    *,
    stdio_format: str = "human",
) -> None:
    timeout = float(os.environ.get("KORU_WUP_COMPOSE_HEALTH_TIMEOUT", "30") or "30")
    if timeout <= 0:
        return
    command = _compose_ps_command(compose_file, profiles, compose_service)
    deadline = time.monotonic() + timeout
    last_status = ""
    while True:
        try:
            result = subprocess.run(
                command,
                cwd=config.project,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            last_status = str(exc)
        else:
            items = _parse_compose_ps_json(result.stdout)
            if result.returncode == 0 and _compose_service_ready(items):
                _wup_stdio_info(
                    f"koru autonomous: WUP compose service ready: {compose_service}",
                    fmt=stdio_format,
                )
                return
            last_status = (result.stderr or result.stdout or "").strip().splitlines()[-1:]
            last_status = last_status[0] if last_status else f"rc={result.returncode}"
        if time.monotonic() >= deadline:
            _wup_stdio_info(
                "koru autonomous: WUP compose readiness timed out for "
                f"{compose_service}: {last_status}",
                fmt=stdio_format,
            )
            return
        time.sleep(1)


def _ensure_wup_profiled_compose_services(
    config: WupWatchConfig,
    *,
    stdio_format: str = "human",
) -> None:
    """Start profiled compose services that WUP live probes depend on."""
    env_flag = os.environ.get("KORU_WUP_COMPOSE_PROFILES", "1").strip().lower()
    if env_flag in {"0", "false", "no", "off"}:
        return
    if shutil.which("docker") is None:
        return
    for compose_file, profiles, compose_service in _profiled_compose_services(config):
        command = ["docker", "compose", "-f", compose_file]
        for profile in profiles:
            command.extend(["--profile", profile])
        command.extend(["up", "-d", compose_service])
        _wup_stdio_info(f"+ {' '.join(command)}", fmt=stdio_format)
        try:
            result = subprocess.run(
                command,
                cwd=config.project,
                check=False,
                capture_output=True,
                text=True,
                timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            _wup_stdio_info(
                f"koru autonomous: WUP compose preflight failed for {compose_service}: {exc}",
                fmt=stdio_format,
            )
            continue
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            _wup_stdio_info(
                f"koru autonomous: WUP compose preflight failed for {compose_service}{suffix}",
                fmt=stdio_format,
            )
            continue
        _wait_for_compose_service_ready(
            config,
            compose_file,
            profiles,
            compose_service,
            stdio_format=stdio_format,
        )


def _start_wup_watch(
    config: WupWatchConfig,
    *,
    topology_integration: bool,
    stdio_format: str = "human",
) -> subprocess.Popen | None:
    from koru.activity_log import activity

    auto = config.enabled is None
    if config.enabled is False:
        activity(
            "WUP",
            "watch disabled by cli",
            fmt=stdio_format,
            data={"project": str(config.project), "mode": config.mode},
        )
        return None
    wup_available = shutil.which("wup") is not None
    wup_yaml_present = (config.project / "wup.yaml").is_file() or config.config is not None
    activity(
        "WUP",
        "watch preflight",
        fmt=stdio_format,
        data={
            "project": str(config.project),
            "auto": auto,
            "enabled": config.enabled,
            "wup_available": wup_available,
            "wup_yaml_present": wup_yaml_present,
            "config": str(config.config) if config.config is not None else "",
            "mode": config.mode,
        },
    )
    if auto:
        if not wup_available or not wup_yaml_present:
            return None
        _wup_stdio_info(
            "koru autonomous: WUP auto-detected (wup.yaml + wup binary present)",
            fmt=stdio_format,
        )
    else:
        if not wup_available:
            _wup_stdio_info(
                "koru autonomous: WUP watch requested but `wup` is not in PATH",
                fmt=stdio_format,
            )
            return None
        if not wup_yaml_present:
            _wup_stdio_info(
                "koru autonomous: WUP watch requested but no wup.yaml found",
                fmt=stdio_format,
            )
            return None
    if not _wup_topology_gate(
        config.project,
        "gate:wup",
        fallback=True,
        enabled=topology_integration,
    ):
        _wup_stdio_info("koru autonomous: WUP watch disabled in topology", fmt=stdio_format)
        return None
    _ensure_wup_profiled_compose_services(config, stdio_format=stdio_format)
    command = _wup_watch_command(config)
    _wup_stdio_info(f"+ {' '.join(command)}", fmt=stdio_format)
    process = subprocess.Popen(command, cwd=config.project, env=_wup_subprocess_env(config))
    activity(
        "WUP",
        "watch process started",
        fmt=stdio_format,
        data={"pid": process.pid, "command": command, "project": str(config.project)},
    )
    _wup_stdio_info(
        f"koru autonomous: started WUP watcher pid={process.pid} mode={config.mode}",
        fmt=stdio_format,
    )
    return process


def _stop_process(
    process: subprocess.Popen | None,
    label: str,
    *,
    stdio_format: str = "human",
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


def _wup_service_names_from_yaml(project: Path) -> set[str] | None:
    """Service names declared in ``wup.yaml`` (``None`` when config is absent)."""
    path = project / "wup.yaml"
    if not path.is_file():
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(payload, dict):
        return None
    services = payload.get("services")
    if not isinstance(services, list):
        return None
    names = {
        str(item["name"])
        for item in services
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    return names or None


def _prune_stale_wup_health(
    health: dict[str, dict],
    *,
    active_services: set[str],
    health_path: Path,
    state_dir: Path,
) -> dict[str, dict]:
    """Drop health rows for services no longer listed in ``wup.yaml``."""
    stale = set(health) - active_services
    if not stale:
        return health
    pruned = {name: data for name, data in health.items() if name in active_services}
    for service in stale:
        diagnostic_marker_path(state_dir, f"wup-{service}").unlink(missing_ok=True)
    try:
        health_path.write_text(
            json.dumps(pruned, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return pruned


def _extract_wup_diagnostic_check_id(ticket: object) -> str | None:
    marker = "[AUTO-DIAG] wup-"
    if isinstance(ticket, dict):
        values = (ticket.get("name", ""), ticket.get("description", ""))
    else:
        values = (getattr(ticket, "name", ""), getattr(ticket, "description", ""))
    for value in values:
        text = str(value or "")
        marker_index = text.find(marker)
        if marker_index < 0:
            continue
        tail = text[marker_index + len("[AUTO-DIAG] ") :]
        check_id = tail.split(" needs attention", 1)[0].strip()
        if check_id.startswith("wup-"):
            return check_id
    return None


def _complete_wup_diagnostic_ticket(ticket: dict, *, note: str) -> None:
    now = datetime.now(UTC).isoformat()
    ticket["status"] = "done"
    ticket["updated_at"] = now
    execution = ticket.setdefault("execution", {})
    if isinstance(execution, dict):
        execution["state"] = "done"
        execution["finished_at"] = now
        execution["last_error"] = None
        execution["lease_expires_at"] = None
    outputs = ticket.setdefault("outputs", {})
    if isinstance(outputs, dict):
        notes = outputs.setdefault("notes", [])
        if isinstance(notes, list):
            notes.append(note)
    history = ticket.setdefault("history", [])
    if isinstance(history, list):
        history.append(
            {
                "timestamp": now,
                "action": "auto_resolved",
                "source": "koru wup",
                "message": note,
            },
        )


def _process_stale_ticket_batch(
    tickets: dict,
    failing_check_ids: set[str],
    state_dir: Path,
) -> bool:
    """Resolve open diagnostic tickets whose check is no longer failing. Returns True if any changed."""
    changed = False
    for ticket in tickets.values():
        if not isinstance(ticket, dict):
            continue
        if str(ticket.get("status") or "").strip().lower() != "open":
            continue
        check_id = _extract_wup_diagnostic_check_id(ticket)
        if not check_id or check_id in failing_check_ids:
            continue
        ticket_id = str(ticket.get("id") or "")
        if not ticket_id:
            continue
        note = f"Auto-resolved by Koru: WUP no longer reports {check_id} as failing."
        _complete_wup_diagnostic_ticket(ticket, note=note)
        diagnostic_marker_path(state_dir, check_id).unlink(missing_ok=True)
        changed = True
    return changed


def _resolve_stale_wup_diagnostic_tickets(
    *,
    project: Path,
    health: dict[str, dict],
    failing: list[str],
    state_dir: Path,
) -> None:
    if not health or not (project / ".planfile").is_dir():
        return
    failing_check_ids = {f"wup-{service}" for service in failing}
    try:
        sprint_path = project / ".planfile" / "sprints" / "current.yaml"
        payload = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return
    sprint = payload.get("sprint") if isinstance(payload, dict) else None
    tickets = sprint.get("tickets") if isinstance(sprint, dict) else None
    if not isinstance(tickets, dict):
        return
    changed = _process_stale_ticket_batch(tickets, failing_check_ids, state_dir)
    if changed:
        try:
            sprint_path.write_text(
                yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )
        except OSError:
            pass


def _identify_failing_services(health: dict[str, dict]) -> list[str]:
    """Identify services with failing status."""
    return [
        service
        for service, data in sorted(health.items())
        if str(data.get("status", "")).lower() in _FAIL_STATUSES
    ]


def _identify_interrupted_services(health: dict[str, dict]) -> list[str]:
    """Identify services whose latest quick run was operator-interrupted."""
    return [
        service
        for service, data in sorted(health.items())
        if str(data.get("status", "")).lower() == "interrupted"
    ]


def _is_interrupted_wup_entry(data: dict) -> bool:
    status = str(data.get("status", "")).strip().lower()
    if status not in _FAIL_STATUSES:
        return False
    message = str(data.get("message") or "").strip().lower()
    return any(marker in message for marker in _INTERRUPTED_MARKERS)


def _normalize_interrupted_wup_health(
    health: dict[str, dict],
    *,
    health_path: Path,
) -> dict[str, dict]:
    """Rewrite transient interrupted failures to status=interrupted.

    Manual operator stops (Ctrl+C) may leave stale ``down: Aborted!`` rows in
    ``service-health.json``. Those should not block autopilot or create
    diagnostic tickets.
    """
    changed = False
    normalized: dict[str, dict] = {}
    for service, data in health.items():
        item = dict(data)
        if _is_interrupted_wup_entry(item):
            item["status"] = "interrupted"
            item["interrupted"] = True
            changed = True
        normalized[service] = item
    if changed:
        try:
            health_path.write_text(
                json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    return normalized


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
            diagnostic_marker_path(state_dir, check_id).unlink(missing_ok=True)


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
    health = _normalize_interrupted_wup_health(health, health_path=health_path)
    active_services = _wup_service_names_from_yaml(project)
    if active_services is not None:
        health = _prune_stale_wup_health(
            health,
            active_services=active_services,
            health_path=health_path,
            state_dir=state_dir,
        )
    failing = _identify_failing_services(health)
    interrupted = _identify_interrupted_services(health)

    if diagnostic_tickets:
        if failing and create_diagnostic_ticket is None:
            raise TypeError("create_diagnostic_ticket is required when diagnostic_tickets is True")
        if create_diagnostic_ticket is not None:
            _create_wup_diagnostic_tickets(
                health,
                failing,
                project,
                ticket_queue,
                state_dir,
                create_diagnostic_ticket,
            )
        _resolve_stale_wup_diagnostic_tickets(
            project=project,
            health=health,
            failing=failing,
            state_dir=state_dir,
        )

    event_count, new_events = _count_wup_events(events_path, state.wup_seen_events)
    state.wup_seen_events = max(state.wup_seen_events, event_count)
    status = "failed" if failing else ("interrupted" if interrupted else ("changed" if new_events else "ok"))
    return WupHealthResult(status=status, failing_services=failing, new_events=new_events)
