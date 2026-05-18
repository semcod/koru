"""Interactive operator pipeline for ``koru auto`` / ``koru autonomous up``.

Probes prerequisites (MCP, autopilot plugin, host injectors, OS calibration),
prints numbered real-time status, and creates planfile tickets on the
``operator`` queue (shell → Taskfile for koru, human for IDE steps).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TextIO

from koru.autonomous_startup import AutonomousStartupProbe
from koru.tasks import CreatedTask, create_nl_task

StepStatus = Literal["ok", "pending", "skipped"]
StepActor = Literal["human", "koru", "taskfile"]


@dataclass(frozen=True)
class OperatorStep:
    step_id: str
    title: str
    actor: StepActor
    status: StepStatus
    detail: str
    task_command: str | None = None
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


def _mcp_koru_configured(project: Path) -> tuple[bool, str]:
    for rel in (".cursor/mcp.json", ".vscode/mcp.json"):
        path = project / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return False, f"nie można odczytać {rel}: {exc}"
        servers = data.get("mcpServers") or {}
        if isinstance(servers, dict) and "koru" in servers:
            return True, f"serwer „koru” w {rel}"
    return False, "brak „koru” w .cursor/mcp.json — task koru:mcp:bootstrap, potem Reload Window"


def _planfile_api_ok(project: Path) -> tuple[bool, str]:
    url = (os.environ.get("KORU_PLANFILE_HEALTH_URL") or "http://127.0.0.1:8765/health").strip()
    try:
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            if 200 <= resp.status < 300:
                return True, f"planfile API OK ({url})"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"planfile API niedostępny ({url}): {exc}"
    return False, f"planfile API nie odpowiada ({url})"


def _os_profile_ok(ide: str, project: Path) -> tuple[bool, str]:
    from koruide import os_injector as oi

    if oi.os_injector_env_disabled():
        return True, "OS injector wyłączony (KORU_OS_INJECTOR=0)"
    profile = oi.try_load_profile(ide, project=project)
    if profile is not None:
        return True, f"profil OS injectora dla {ide} ({profile.chat_x}, {profile.chat_y})"
    return False, f"brak kalibracji chatu dla {ide} — task koru:ide-os:calibrate IDE={ide}"


def _host_injectors_ok() -> tuple[bool, str]:
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


def build_operator_steps(
    *,
    project: Path,
    probe: AutonomousStartupProbe,
    plugin_connected: bool | None,
    mcp_already_bootstrapped: bool = False,
) -> list[OperatorStep]:
    """Return ordered steps with probe status (no ticket I/O)."""
    ide = probe.resolved_autopilot_ide
    steps: list[OperatorStep] = []

    api_ok, api_detail = _planfile_api_ok(project)
    steps.append(
        OperatorStep(
            step_id="planfile_api",
            title="Planfile API (dashboard / kolejka)",
            actor="taskfile",
            status="ok" if api_ok else "pending",
            detail=api_detail,
            task_command=None if api_ok else "task koru:server",
        )
    )

    mcp_ok, mcp_detail = _mcp_koru_configured(project)
    if mcp_already_bootstrapped and not mcp_ok:
        mcp_detail += " (bootstrap właśnie wykonany — zrób Reload Window w IDE)"
    steps.append(
        OperatorStep(
            step_id="mcp_koru",
            title="MCP „koru” w IDE",
            actor="taskfile",
            status="ok" if mcp_ok else "pending",
            detail=mcp_detail,
            task_command=None if mcp_ok else "task koru:mcp:bootstrap",
        )
    )

    if plugin_connected is True:
        plug_status: StepStatus = "ok"
        plug_detail = f"plugin połączony (ide={ide})"
        plug_task = None
    elif plugin_connected is False:
        plug_status = "pending"
        plug_detail = f"brak pluginu na {probe.socket_path}"
        plug_task = "task koru:operator:plugin-probe"
    else:
        plug_status = "pending"
        plug_detail = "nie sprawdzono — podłącz plugin w IDE"
        plug_task = "task koru:operator:plugin-probe"

    steps.append(
        OperatorStep(
            step_id="autopilot_plugin",
            title="Autopilot: Connect + plugin w czacie",
            actor="human",
            status=plug_status,
            detail=plug_detail,
            task_command=plug_task,
        )
    )

    host_ok, host_detail = _host_injectors_ok()
    steps.append(
        OperatorStep(
            step_id="host_injectors",
            title="Zależności hosta (xdotool / wtype / ydotool)",
            actor="taskfile",
            status="ok" if host_ok else "pending",
            detail=host_detail,
            task_command=None if host_ok else "task koru:operator:setup-host",
        )
    )

    prof_ok, prof_detail = _os_profile_ok(ide, project)
    steps.append(
        OperatorStep(
            step_id="os_calibrate",
            title=f"Kalibracja czatu OS injectora ({ide})",
            actor="human",
            status="ok" if prof_ok else "pending",
            detail=prof_detail,
            task_command=None if prof_ok else f"task koru:ide-os:calibrate IDE={ide}",
        )
    )

    steps.append(
        OperatorStep(
            step_id="ready",
            title="Gotowość: pętla scan → queue → IDE",
            actor="koru",
            status="ok",
            detail="Koru kontynuuje cykle; tickety operatora można zamykać równolegle",
            task_command=None,
        )
    )
    return steps


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
    line = (
        f"koru autonomous: [{index}/{total}] {mark} {step.title} [{actor}] — {step.detail}"
    )
    activity(
        "OPERATOR",
        f"[{index}/{total}] {mark} {step.title} [{actor}] — {step.detail}",
        fmt=fmt,
    )
    stream.write(line + "\n")
    if step.task_command and step.status == "pending":
        stream.write(f"koru autonomous:     uruchom: {step.task_command}\n")
    if step.ticket_id:
        stream.write(
            f"koru autonomous:     ticket {step.ticket_id} (kolejka operator)\n"
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
            "source_context": {"step_id": step.step_id},
        }
    else:
        script = step.task_command or "true"
        prompt = f"[OPERATOR] {step.title}: {step.detail}\n\nShell: `{script}`"
        scaffold = {
            "executor_kind": "shell",
            "executor_mode": "noninteractive",
            "labels": labels,
            "source_tool": "koru-operator-pipeline",
            "source_context": {"step_id": step.step_id},
            "inputs": {"script": script},
        }

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
        "pętla główna (scan/queue/IDE) działa równolegle.\n"
    )
    out.flush()

    state_dir = _operator_state_dir(project)
    for i, step in enumerate(steps, start=1):
        ticket_id: str | None = _read_marker(state_dir, step.step_id)
        if create_tickets and step.status == "pending" and ticket_id is None:
            created = _create_step_ticket(
                project,
                step,
                queue_name=ticket_queue,
                priority=ticket_priority,
                state_dir=state_dir,
                stdio_format=stdio_format,
            )
            if created is not None:
                ticket_id = created.ticket_id
                result.tickets_created.append(ticket_id)
        step = OperatorStep(
            step_id=step.step_id,
            title=step.title,
            actor=step.actor,
            status=step.status,
            detail=step.detail,
            task_command=step.task_command,
            ticket_id=ticket_id,
        )
        result.steps.append(step)
        _emit_step(out, index=i, total=total, step=step, fmt=stdio_format)
        if stdio_format == "jsonl" and correlation_id:
            from koru.stdio_events import write_stdio_event

            write_stdio_event(
                out,
                event_type="OperatorStep",
                correlation_id=correlation_id,
                payload={
                    "index": i,
                    "total": total,
                    "step_id": step.step_id,
                    "status": step.status,
                    "actor": step.actor,
                    "ticket_id": ticket_id,
                    "task_command": step.task_command,
                },
            )

    pending = sum(1 for s in result.steps if s.status == "pending")
    out.write(
        f"koru autonomous: pipeline operatora: {pending} krok(ów) do zrobienia, "
        f"{len(result.tickets_created)} nowych ticketów\n"
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
