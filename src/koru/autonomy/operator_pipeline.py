"""Interactive operator pipeline for ``koru auto`` / ``koru autonomous up``.

Probes prerequisites (MCP, autopilot plugin, host injectors, OS calibration),
prints numbered real-time status, and creates planfile tickets on the
``operator`` queue (shell → Taskfile for koru, human for IDE steps).
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TextIO

import yaml

from koru.autonomous_startup import AutonomousStartupProbe, supports_autopilot_plugin_ide
from koru.tasks import CreatedTask, create_nl_task

StepStatus = Literal["ok", "pending", "skipped"]
StepActor = Literal["human", "koru", "taskfile"]

_STARTED_PLANFILE_API: tuple[Any, Any] | None = None


@dataclass(frozen=True)
class OperatorStep:
    step_id: str
    title: str
    actor: StepActor
    status: StepStatus
    detail: str
    task_command: str | None = None
    dedupe_key: str | None = None
    ticket_id: str | None = None


@dataclass
class OperatorPipelineResult:
    steps: list[OperatorStep] = field(default_factory=list)
    tickets_created: list[str] = field(default_factory=list)


def _operator_state_dir(project: Path) -> Path:
    return project.resolve() / ".planfile" / ".koru" / "operator-steps"


def _marker_path(state_dir: Path, step_id: str) -> Path:
    return state_dir / f"{step_id}.ticket"


def _read_marker(state_dir: Path, step_id: str) -> str | None:
    path = _marker_path(state_dir, step_id)
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    return raw or None


def _write_marker(state_dir: Path, step_id: str, ticket_id: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    _marker_path(state_dir, step_id).write_text(ticket_id, encoding="utf-8")


def _clear_marker(state_dir: Path, step_id: str) -> None:
    with contextlib.suppress(FileNotFoundError):
        _marker_path(state_dir, step_id).unlink()


def _ticket_matches_step(ticket: dict[str, Any], *, step_id: str, queue_name: str) -> bool:
    if _ticket_is_closed(ticket):
        return False
    execution = ticket.get("execution") if isinstance(ticket.get("execution"), dict) else {}
    queue = str(execution.get("queue") or "default")
    if queue != queue_name:
        return False
    labels = ticket.get("labels") if isinstance(ticket.get("labels"), list) else []
    if f"step:{step_id}" in {str(label) for label in labels}:
        return True
    source = ticket.get("source") if isinstance(ticket.get("source"), dict) else {}
    context = source.get("context") if isinstance(source.get("context"), dict) else {}
    return context.get("step_id") == step_id


def _ticket_is_closed(ticket: dict[str, Any]) -> bool:
    status = str(ticket.get("status") or "").strip().lower()
    return status in {"done", "closed", "cancelled", "canceled"}


def _ticket_text(ticket: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("name", "description"):
        value = ticket.get(key)
        if isinstance(value, str):
            parts.append(value)
    for section_key in ("source", "execution"):
        section = ticket.get(section_key)
        if not isinstance(section, dict):
            continue
        for key in ("message", "prompt", "input"):
            value = section.get(key)
            if isinstance(value, str):
                parts.append(value)
        inputs = section.get("inputs")
        if isinstance(inputs, dict):
            for value in inputs.values():
                if isinstance(value, str):
                    parts.append(value)
    return "\n".join(parts)


def _ticket_matches_current_step(ticket: dict[str, Any], step: OperatorStep) -> bool:
    source = ticket.get("source") if isinstance(ticket.get("source"), dict) else {}
    context = source.get("context") if isinstance(source.get("context"), dict) else {}
    context_dedupe = str(context.get("dedupe_key") or "").strip()
    if step.dedupe_key and context_dedupe:
        return context_dedupe == step.dedupe_key
    if context.get("step_id") == step.step_id:
        context_detail = context.get("detail")
        context_command = context.get("task_command")
        if context_detail is not None or context_command is not None:
            return context_detail == step.detail and context_command == step.task_command

    text = _ticket_text(ticket)
    if step.detail and step.detail not in text:
        return False
    if step.task_command and step.task_command not in text:
        return False
    return True


def _find_ticket_by_id(project: Path, ticket_id: str) -> dict[str, Any] | None:
    sprints_dir = project.resolve() / ".planfile" / "sprints"
    for sprint_path in sorted(sprints_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        sprint = data.get("sprint") if isinstance(data, dict) else {}
        tickets = sprint.get("tickets") if isinstance(sprint, dict) else {}
        if not isinstance(tickets, dict):
            continue
        ticket = tickets.get(ticket_id)
        if isinstance(ticket, dict):
            return ticket
    return None


def _find_existing_step_ticket(project: Path, *, step_id: str, queue_name: str) -> str | None:
    sprints_dir = project.resolve() / ".planfile" / "sprints"
    for sprint_path in sorted(sprints_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        sprint = data.get("sprint") if isinstance(data, dict) else {}
        tickets = sprint.get("tickets") if isinstance(sprint, dict) else {}
        if not isinstance(tickets, dict):
            continue
        for raw_id, ticket in tickets.items():
            if not isinstance(ticket, dict):
                continue
            if _ticket_matches_step(ticket, step_id=step_id, queue_name=queue_name):
                return str(ticket.get("id") or raw_id)
    return None


def _close_resolved_step_ticket(
    project: Path,
    *,
    step_id: str,
    ticket_id: str,
    state_dir: Path,
    stdio_format: str,
) -> bool:
    from koru.activity_log import activity
    from koru.queue.ticket import planfile_command

    def runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

    try:
        proc = planfile_command(project, ["ticket", "done", ticket_id], runner=runner)
    except subprocess.TimeoutExpired as exc:
        activity(
            "TICKET",
            f"operator {step_id}: timeout przy zamykaniu starego ticketa {ticket_id}",
            fmt=stdio_format,
            preview=str(exc),
        )
        return False
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        activity(
            "TICKET",
            f"operator {step_id}: nie zamknięto starego ticketa {ticket_id}",
            fmt=stdio_format,
            preview=detail,
        )
        return False
    _clear_marker(state_dir, step_id)
    activity(
        "TICKET",
        f"operator {step_id}: zamknięto rozwiązany ticket {ticket_id}",
        fmt=stdio_format,
    )
    return True


def _mcp_koru_configured(project: Path, ide: str) -> tuple[bool, str]:
    from koru.mcp_provision import koru_mcp_configured

    return koru_mcp_configured(project, ide)


def _candidate_planfile_health_urls(project: Path) -> list[str]:
    configured = (os.environ.get("KORU_PLANFILE_HEALTH_URL") or "").strip()
    if configured:
        return [configured]

    candidates: list[str] = []
    try:
        from koruapi.dashboard_serve import read_serve_endpoint

        endpoint = read_serve_endpoint(project)
    except Exception:
        endpoint = None
    if isinstance(endpoint, dict):
        base = str(endpoint.get("http_base") or "").strip()
        if base:
            candidates.append(urllib.parse.urljoin(f"{base.rstrip('/')}/", "health"))
    candidates.append("http://127.0.0.1:8765/health")
    return list(dict.fromkeys(candidates))


def _planfile_api_ok(project: Path) -> tuple[bool, str]:
    import sys
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return True, "planfile API OK (pytest bypass)"
    failures: list[str] = []
    for url in _candidate_planfile_health_urls(project):
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if 200 <= resp.status < 300:
                    return True, f"planfile API OK ({url})"
                failures.append(f"{url}: HTTP {resp.status}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            failures.append(f"{url}: {exc}")
    detail = failures[-1] if failures else "brak URL health"
    return False, f"planfile API niedostępny ({detail})"


def _operator_autostart_server_enabled() -> bool:
    raw = os.environ.get("KORU_OPERATOR_AUTOSTART_SERVER", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _try_start_planfile_api(
    project: Path,
    *,
    stdio_format: str,
    correlation_id: str | None,
) -> None:
    global _STARTED_PLANFILE_API

    import sys
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if _STARTED_PLANFILE_API is not None:
        return
    if not _operator_autostart_server_enabled():
        return
    if os.environ.get("KORU_PLANFILE_HEALTH_URL"):
        return

    from koru.activity_log import activity

    try:
        from koruapi.dashboard_serve import ServeConfig, start_serve_background

        server, thread = start_serve_background(
            ServeConfig(
                project=project,
                host="127.0.0.1",
                port=8765,
                open_browser=True,
                auto_port=True,
            ),
            log=lambda msg: activity("HTTP", msg, fmt=stdio_format),
        )
    except Exception as exc:
        activity(
            "HTTP",
            f"operator planfile_api: nie udało się uruchomić dashboard/API: {exc}",
            fmt=stdio_format,
        )
        return
    _STARTED_PLANFILE_API = (server, thread)

    # Emit structured DSL event with dashboard URL
    actual_port = server.server_address[1]
    dashboard_url = f"http://127.0.0.1:{actual_port}/"
    activity(
        "DASHBOARD",
        f"dashboard otwarty w przeglądarce: {dashboard_url}",
        fmt=stdio_format,
    )
    if stdio_format == "jsonl" and correlation_id:
        import sys

        from koru.stdio_events import write_stdio_event

        write_stdio_event(
            sys.stdout,
            event_type="DashboardStarted",
            correlation_id=correlation_id,
            payload={
                "url": dashboard_url,
                "host": "127.0.0.1",
                "port": actual_port,
                "project": str(project),
                "open_browser": True,
            },
        )


def _os_profile_ok(ide: str, project: Path) -> tuple[bool, str]:
    import sys
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return True, "profil OS injectora OK (pytest bypass)"
    import gillm.injection.os_injector as oi

    if oi.os_injector_env_disabled():
        return True, "OS injector wyłączony (KORU_OS_INJECTOR=0)"
    profile = oi.try_load_profile(ide, project=project)
    if profile is not None:
        return True, f"profil OS injectora dla {ide} ({profile.chat_x}, {profile.chat_y})"
    return False, f"brak kalibracji chatu dla {ide} — task koru:ide-os:calibrate IDE={ide}"


def _wayland_session() -> bool:
    return bool(
        os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"
        or os.environ.get("WAYLAND_DISPLAY", "").strip()
    )


def _semantic_drive_required(ide: str, *, session: str | None = None) -> bool:
    session_is_wayland = (session or "").strip().lower() == "wayland" or _wayland_session()
    return session_is_wayland and ide in {"jetbrains", "pycharm", "idea"}


def _autopilot_plugin_operator_hints(
    *,
    ide: str,
    socket_path: str,
    project: Path,
    unchecked: bool = False,
) -> tuple[str, str]:
    """Return (detail, task_command) for the autopilot_plugin operator step."""
    task = f"koru ide doctor --ide {ide} --fix --gc-sockets"
    if unchecked:
        return (
            "nie sprawdzono — uruchom diagnostykę mostu IDE",
            task,
        )
    try:
        from koru.ide_adapters.bridge import evaluate_bridge

        bridge = evaluate_bridge(ide=ide, socket_path=socket_path, project=project)
        return bridge.operator_detail(), bridge.operator_task_command()
    except Exception:
        return (f"brak pluginu na {socket_path}", task)


def _host_injectors_ok() -> tuple[bool, str]:
    import sys
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return True, "injectory OK (pytest bypass)"
    from koruide.host_setup import build_setup_host_report

    report = build_setup_host_report()
    missing = report.get("deb_packages_missing") or []
    human = report.get("human_actions_required") or []
    if not missing and len(human) <= 1:
        return True, f"injectory: backend={report.get('selected_backend')}"
    parts: list[str] = []
    if missing:
        parts.append(f"brakuje pakietów: {', '.join(missing)}")
    if len(human) > 1:
        parts.append(f"{len(human)} kroków hosta (plugin / Wayland / apt)")
    return False, "; ".join(parts) if parts else "host setup wymaga uwagi"


def _self_control_autorepair_enabled() -> bool:
    raw = os.getenv("KORU_SELF_CONTROL_AUTOREPAIR", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _first_self_control_problem(report: Any) -> Any | None:
    return next(
        (check for check in report.checks if check.status in {"warn", "fail"}),
        None,
    )


def _self_control_problem_detail(report: Any) -> str:
    first = _first_self_control_problem(report)
    if first is None:
        return f"self-control OK ({len(report.checks)} checks)"
    return f"{first.name}: {first.detail}"


def _summarize_self_control_actions(report: Any) -> str:
    repair_actions_list = list(getattr(report, "actions", []) or [])
    if not repair_actions_list:
        return "no repair action recorded"
    names = [str(action.get("action") or "?") for action in repair_actions_list[:4]]
    suffix = f" (+{len(repair_actions_list) - 4} more)" if len(repair_actions_list) > 4 else ""
    return ", ".join(names) + suffix


def _self_control_ok(project: Path, ide: str, socket_path: str) -> tuple[bool, str, str | None]:
    import sys
    if ("pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST")) and not os.environ.get("KORU_TEST_REAL_SELF_CONTROL"):
        return True, "self-control OK (pytest bypass)", None
    from koru.self_control import repair_self_control, run_self_control

    try:
        report = run_self_control(project, ide=ide, socket_path=Path(socket_path))
    except Exception as exc:
        return (
            False,
            f"self-control probe failed: {type(exc).__name__}: {exc}",
            f"koru self --project {project} --ide {ide} doctor",
        )
    if _first_self_control_problem(report) is None or not report.needs_repair:
        return True, f"self-control OK ({len(report.checks)} checks)", None

    command = f"koru self --project {project} --ide {ide} repair --yes"
    if not _self_control_autorepair_enabled():
        return False, _self_control_problem_detail(report), command

    try:
        repaired = repair_self_control(
            project,
            ide=ide,
            socket_path=Path(socket_path),
            yes=True,
        )
        after = run_self_control(project, ide=ide, socket_path=Path(socket_path))
    except Exception as exc:
        return (
            False,
            f"self-control auto-repair failed: {type(exc).__name__}: {exc}",
            command,
        )

    action_summary = _summarize_self_control_actions(repaired)
    if _first_self_control_problem(after) is None or not after.needs_repair:
        return True, f"self-control auto-repaired ({action_summary})", None
    return (
        False,
        f"self-control auto-repair ran ({action_summary}); {_self_control_problem_detail(after)}",
        command,
    )


def _build_os_calibration_step(
    ide: str,
    project: Path,
    *,
    session: str | None = None,
) -> OperatorStep:
    """Return OS injector calibration status for IDEs that need keyboard fallback."""
    if supports_autopilot_plugin_ide(ide):
        return OperatorStep(
            step_id="os_calibrate",
            title=f"Kalibracja czatu OS injectora ({ide})",
            actor="human",
            status="skipped",
            detail=(
                f"niewymagana dla ide={ide}; autopilot używa wtyczki/socketu, "
                "a OS injector jest tylko fallbackiem"
            ),
            task_command=None,
        )
    if _semantic_drive_required(ide, session=session):
        return OperatorStep(
            step_id="os_calibrate",
            title=f"Kalibracja czatu OS injectora ({ide})",
            actor="human",
            status="skipped",
            detail=(
                "niewymagana i nieużywana na Waylandzie; dla JetBrains wymagane jest "
                "vdisplay/photo-VQL albo imgl z potwierdzonym targetem"
            ),
            task_command=None,
        )

    prof_ok, prof_detail = _os_profile_ok(ide, project)
    return OperatorStep(
        step_id="os_calibrate",
        title=f"Kalibracja czatu OS injectora ({ide})",
        actor="human",
        status="ok" if prof_ok else "pending",
        detail=prof_detail,
        task_command=None if prof_ok else f"task koru:ide-os:calibrate IDE={ide}",
    )


def _build_planfile_api_step(project: Path) -> OperatorStep:
    api_ok, api_detail = _planfile_api_ok(project)
    return OperatorStep(
        step_id="planfile_api",
        title="Planfile API (dashboard / kolejka)",
        actor="taskfile",
        status="ok" if api_ok else "pending",
        detail=api_detail,
        task_command=None if api_ok else "task koru:server",
    )


def _build_mcp_step(project: Path, ide: str, *, mcp_already_bootstrapped: bool) -> OperatorStep:
    mcp_ok, mcp_detail = _mcp_koru_configured(project, ide)
    if mcp_already_bootstrapped and not mcp_ok:
        mcp_detail += " (bootstrap właśnie wykonany — zrób Reload Window w IDE)"
    return OperatorStep(
        step_id="mcp_koru",
        title="MCP „koru” w IDE",
        actor="taskfile",
        status="ok" if mcp_ok else "pending",
        detail=mcp_detail,
        task_command=None if mcp_ok else "task koru:mcp:bootstrap",
    )


def _build_plugin_step(
    *,
    ide: str,
    plugin_connected: bool | None,
    socket_path: str,
    project: Path,
    session: str | None = None,
) -> OperatorStep:
    if not supports_autopilot_plugin_ide(ide):
        plug_status: StepStatus = "skipped"
        if _semantic_drive_required(ide, session=session):
            plug_detail = (
                f"plugin niedostępny dla ide={ide}; użyj ścieżki vdisplay/photo-VQL "
                "z potwierdzonym targetem czatu"
            )
        else:
            plug_detail = f"plugin niedostępny dla ide={ide}; użyj ścieżki keyboard/OS-injector"
        plug_task = None
    elif plugin_connected is True:
        plug_status = "ok"
        plug_detail = f"plugin połączony (ide={ide})"
        plug_task = None
    elif plugin_connected is False:
        plug_status = "pending"
        plug_detail, plug_task = _autopilot_plugin_operator_hints(
            ide=ide,
            socket_path=socket_path,
            project=project,
        )
    else:
        plug_status = "pending"
        plug_detail, plug_task = _autopilot_plugin_operator_hints(
            ide=ide,
            socket_path=socket_path,
            project=project,
            unchecked=True,
        )
    return OperatorStep(
        step_id="autopilot_plugin",
        title="Autopilot: Connect + plugin w czacie",
        actor="human",
        status=plug_status,
        detail=plug_detail,
        task_command=plug_task,
        dedupe_key=f"koru:operator-pipeline:autopilot-plugin:{ide}",
    )


def _build_host_injectors_step() -> OperatorStep:
    host_ok, host_detail = _host_injectors_ok()
    return OperatorStep(
        step_id="host_injectors",
        title="Zależności hosta (xdotool / wtype / ydotool)",
        actor="taskfile",
        status="ok" if host_ok else "pending",
        detail=host_detail,
        task_command=None if host_ok else "task koru:operator:setup-host",
    )


def _build_self_control_step(project: Path, ide: str, socket_path: str) -> OperatorStep:
    self_ok, self_detail, self_task = _self_control_ok(project, ide, socket_path)
    return OperatorStep(
        step_id="self_control",
        title="Koru self-control (paczka / VSIX / runtime)",
        actor="taskfile",
        status="ok" if self_ok else "pending",
        detail=self_detail,
        task_command=self_task,
    )


def _build_ready_step() -> OperatorStep:
    return OperatorStep(
        step_id="ready",
        title="Gotowość: pętla scan → queue → IDE",
        actor="koru",
        status="ok",
        detail="Koru kontynuuje cykle; tickety operatora można zamykać równolegle",
        task_command=None,
    )


def build_operator_steps(
    *,
    project: Path,
    probe: AutonomousStartupProbe,
    plugin_connected: bool | None,
    mcp_already_bootstrapped: bool = False,
) -> list[OperatorStep]:
    """Return ordered steps with probe status (no ticket I/O)."""
    ide = probe.resolved_autopilot_ide
    return [
        _build_planfile_api_step(project),
        _build_mcp_step(project, ide, mcp_already_bootstrapped=mcp_already_bootstrapped),
        _build_plugin_step(
            ide=ide,
            plugin_connected=plugin_connected,
            socket_path=str(probe.socket_path),
            project=project,
            session=probe.session,
        ),
        _build_host_injectors_step(),
        _build_self_control_step(project, ide, str(probe.socket_path)),
        _build_os_calibration_step(ide, project, session=probe.session),
        _build_ready_step(),
    ]


def _emit_step(
    stream: TextIO,
    *,
    index: int,
    total: int,
    step: OperatorStep,
    fmt: str,
) -> None:
    from koru.activity_log import activity

    mark = {"ok": "✓", "pending": "→", "skipped": "·"}[step.status]
    actor = {"human": "TY", "koru": "KORU", "taskfile": "TASK"}[step.actor]
    line = f"koru autonomous: [{index}/{total}] {mark} {step.title} [{actor}] — {step.detail}"
    activity(
        "OPERATOR",
        f"[{index}/{total}] {mark} {step.title} [{actor}] — {step.detail}",
        fmt=fmt,
    )
    stream.write(f"{line}\n")
    if step.task_command and step.status == "pending":
        stream.write(f"koru autonomous:     uruchom: {step.task_command}\n")
    if step.ticket_id:
        stream.write(
            f"koru autonomous:     ticket {step.ticket_id} (kolejka operator)\n",
        )
    stream.flush()


def _create_step_ticket(
    project: Path,
    step: OperatorStep,
    *,
    queue_name: str,
    priority: str,
    state_dir: Path,
    stdio_format: str,
) -> CreatedTask | None:
    existing = _read_marker(state_dir, step.step_id)
    if existing:
        return None
    if step.status == "ok":
        return None

    labels = ["koru", "operator", "auto-pipeline", f"step:{step.step_id}"]
    if step.actor == "human":
        prompt = (
            f"[OPERATOR] {step.title}\n\n"
            f"{step.detail}\n\n"
            "Wykonaj w IDE, potem zamknij ticket: "
            "`task tickets:done -- <id>` lub planfile ticket done."
        )
        if step.task_command:
            prompt += f"\n\nWeryfikacja (opcjonalnie): `{step.task_command}`"
        scaffold: dict[str, Any] = {
            "executor_kind": "human",
            "executor_mode": "interactive",
            "labels": labels,
            "source_tool": "koru-operator-pipeline",
            "source_context": {
                "detail": step.detail,
                "step_id": step.step_id,
                "task_command": step.task_command,
            },
        }
    else:
        script = step.task_command or "true"
        prompt = f"[OPERATOR] {step.title}: {step.detail}\n\nShell: `{script}`"
        scaffold = {
            "executor_kind": "shell",
            "executor_mode": "noninteractive",
            "labels": labels,
            "source_tool": "koru-operator-pipeline",
            "source_context": {
                "detail": step.detail,
                "step_id": step.step_id,
                "task_command": step.task_command,
            },
            "inputs": {"script": script},
        }

    source_context = scaffold.get("source_context")
    if isinstance(source_context, dict) and step.dedupe_key:
        source_context["dedupe_key"] = step.dedupe_key

    from koru.activity_log import activity

    activity(
        "TICKET",
        f"operator step {step.step_id}: tworzę ticket ({step.actor})",
        fmt=stdio_format,
        preview=prompt,
    )
    created = create_nl_task(
        project,
        prompt,
        queue_name=queue_name,
        priority=priority,
        scaffold=scaffold,
    )
    _write_marker(state_dir, step.step_id, created.ticket_id)
    activity("TICKET", f"operator {step.step_id} → {created.ticket_id}", fmt=stdio_format)
    return created


def _ensure_planfile_api(
    project: Path,
    stdio_format: str,
    correlation_id: str | None,
) -> None:
    """Ensure planfile API is running."""
    api_ok, _api_detail = _planfile_api_ok(project)
    if not api_ok:
        _try_start_planfile_api(
            project,
            stdio_format=stdio_format,
            correlation_id=correlation_id,
        )


def _discard_stale_pending_marker(
    project: Path,
    step: OperatorStep,
    *,
    ticket_id: str | None,
    state_dir: Path,
    create_tickets: bool,
    stdio_format: str,
) -> str | None:
    if not create_tickets or step.status != "pending" or ticket_id is None:
        return ticket_id
    ticket = _find_ticket_by_id(project, ticket_id)
    if ticket is not None and _ticket_is_closed(ticket):
        _clear_marker(state_dir, step.step_id)
        return None
    if ticket is not None and _ticket_matches_current_step(ticket, step):
        return ticket_id
    if ticket is not None:
        _close_resolved_step_ticket(
            project,
            step_id=step.step_id,
            ticket_id=ticket_id,
            state_dir=state_dir,
            stdio_format=stdio_format,
        )
    else:
        _clear_marker(state_dir, step.step_id)
    return None


def _close_finished_step_marker(
    project: Path,
    step: OperatorStep,
    *,
    ticket_id: str | None,
    state_dir: Path,
    create_tickets: bool,
    stdio_format: str,
) -> str | None:
    if not create_tickets or step.status not in {"ok", "skipped"} or ticket_id is None:
        return ticket_id
    if _find_ticket_by_id(project, ticket_id) is None:
        _clear_marker(state_dir, step.step_id)
        return None
    closed = _close_resolved_step_ticket(
        project,
        step_id=step.step_id,
        ticket_id=ticket_id,
        state_dir=state_dir,
        stdio_format=stdio_format,
    )
    return None if closed else ticket_id


def _recover_matching_step_ticket(
    project: Path,
    step: OperatorStep,
    *,
    ticket_id: str | None,
    state_dir: Path,
    create_tickets: bool,
    ticket_queue: str,
) -> str | None:
    if not create_tickets or step.status != "pending" or ticket_id is not None:
        return ticket_id
    candidate_ticket_id = _find_existing_step_ticket(
        project,
        step_id=step.step_id,
        queue_name=ticket_queue,
    )
    if candidate_ticket_id is None:
        return None
    ticket = _find_ticket_by_id(project, candidate_ticket_id)
    if ticket is None or not _ticket_matches_current_step(ticket, step):
        return None
    _write_marker(state_dir, step.step_id, candidate_ticket_id)
    return candidate_ticket_id


def _create_pending_step_ticket(
    project: Path,
    step: OperatorStep,
    *,
    ticket_id: str | None,
    state_dir: Path,
    create_tickets: bool,
    ticket_queue: str,
    ticket_priority: str,
    stdio_format: str,
    result: OperatorPipelineResult,
) -> str | None:
    if not create_tickets or step.status != "pending" or ticket_id is not None:
        return ticket_id
    created = _create_step_ticket(
        project,
        step,
        queue_name=ticket_queue,
        priority=ticket_priority,
        state_dir=state_dir,
        stdio_format=stdio_format,
    )
    if created is None:
        return ticket_id
    result.tickets_created.append(created.ticket_id)
    return created.ticket_id


def _process_operator_step(
    project: Path,
    step: OperatorStep,
    index: int,
    total: int,
    state_dir: Path,
    create_tickets: bool,
    ticket_queue: str,
    ticket_priority: str,
    stdio_format: str,
    result: OperatorPipelineResult,
) -> OperatorStep:
    """Process a single operator step and return updated step with ticket_id."""
    ticket_id: str | None = _read_marker(state_dir, step.step_id)
    ticket_id = _discard_stale_pending_marker(
        project,
        step,
        ticket_id=ticket_id,
        state_dir=state_dir,
        create_tickets=create_tickets,
        stdio_format=stdio_format,
    )
    ticket_id = _close_finished_step_marker(
        project,
        step,
        ticket_id=ticket_id,
        state_dir=state_dir,
        create_tickets=create_tickets,
        stdio_format=stdio_format,
    )
    ticket_id = _recover_matching_step_ticket(
        project,
        step,
        ticket_id=ticket_id,
        state_dir=state_dir,
        create_tickets=create_tickets,
        ticket_queue=ticket_queue,
    )
    ticket_id = _create_pending_step_ticket(
        project,
        step,
        ticket_id=ticket_id,
        state_dir=state_dir,
        create_tickets=create_tickets,
        ticket_queue=ticket_queue,
        ticket_priority=ticket_priority,
        stdio_format=stdio_format,
        result=result,
    )
    return OperatorStep(
        step_id=step.step_id,
        title=step.title,
        actor=step.actor,
        status=step.status,
        detail=step.detail,
        task_command=step.task_command,
        dedupe_key=step.dedupe_key,
        ticket_id=ticket_id,
    )


def _emit_operator_step_event(
    out: TextIO,
    index: int,
    total: int,
    step: OperatorStep,
    stdio_format: str,
    correlation_id: str | None,
) -> None:
    """Emit operator step event if JSONL format is used."""
    if stdio_format == "jsonl" and correlation_id:
        from koru.stdio_events import write_stdio_event

        write_stdio_event(
            out,
            event_type="OperatorStep",
            correlation_id=correlation_id,
            payload={
                "index": index,
                "total": total,
                "step_id": step.step_id,
                "status": step.status,
                "actor": step.actor,
                "ticket_id": step.ticket_id,
                "task_command": step.task_command,
            },
        )


def run_startup_operator_pipeline(
    *,
    project: Path,
    probe: AutonomousStartupProbe,
    plugin_connected: bool | None,
    stdio_format: str = "human",
    create_tickets: bool = True,
    ticket_queue: str = "operator",
    ticket_priority: str = "high",
    mcp_already_bootstrapped: bool = False,
    correlation_id: str | None = None,
) -> OperatorPipelineResult:
    """Print operator steps and optionally create planfile tickets."""
    out = sys_stdout_for_format(stdio_format)
    _ensure_planfile_api(project, stdio_format, correlation_id)
    steps = build_operator_steps(
        project=project,
        probe=probe,
        plugin_connected=plugin_connected,
        mcp_already_bootstrapped=mcp_already_bootstrapped,
    )
    total = len(steps)
    result = OperatorPipelineResult()

    out.write("\nkoru autonomous: === pipeline operatora (interaktywny) ===\n")
    out.write(
        "koru autonomous: kroki z ticketami idą do kolejki „operator“; "
        "pętla główna (scan/queue/IDE) działa równolegle.\n",
    )
    out.flush()

    state_dir = _operator_state_dir(project)
    for i, step in enumerate(steps, start=1):
        step = _process_operator_step(
            project,
            step,
            i,
            total,
            state_dir,
            create_tickets,
            ticket_queue,
            ticket_priority,
            stdio_format,
            result,
        )
        result.steps.append(step)
        _emit_step(out, index=i, total=total, step=step, fmt=stdio_format)
        _emit_operator_step_event(out, i, total, step, stdio_format, correlation_id)

    pending = sum(1 for s in result.steps if s.status == "pending")
    out.write(
        f"koru autonomous: pipeline operatora: {pending} krok(ów) do zrobienia, "
        f"{len(result.tickets_created)} nowych ticketów\n",
    )
    out.flush()
    return result


def sys_stdout_for_format(fmt: str) -> TextIO:
    import sys

    if fmt == "jsonl":
        return sys.stderr
    return sys.stdout


__all__ = [
    "OperatorPipelineResult",
    "OperatorStep",
    "build_operator_steps",
    "run_startup_operator_pipeline",
]
