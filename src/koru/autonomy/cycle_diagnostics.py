"""Idle-diagnostics helpers for the autonomous cycle.

Extracted verbatim from ``koru.autonomy.cycle.cycle`` (STARTER-545). The legacy
``_underscored`` names remain importable from ``koru.autonomy.cycle.cycle`` via
``import as`` re-exports so existing tests/callers keep working unchanged.

Cross-module calls to names that tests (or ``run_cycle_with_compat``)
monkeypatch on the facade are resolved late via
``from koru import autonomous_cycle as _cycle_mod`` at call time.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from koru.autonomy.cycle.cycle_common import DiagnosticResult
from koru.autonomy.cycle.cycle_skip_conditions import _is_topology_enabled
from koru.autonomy.operator.operator_wup import WupHealthResult
from koru.autonomy.operator.operator_wup import _read_wup_health as _read_wup_health_impl
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult


def _current_head(project: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _run_command_check(
    project: Path,
    check_id: str,
    command: list[str],
    *,
    stdio_format: str = "human",
) -> bool:
    from koru import autonomous_cycle as _cycle_mod

    _cycle_mod._stdio_info(f"+ {' '.join(command)}", fmt=stdio_format)
    result = subprocess.run(command, cwd=project, check=False)
    if result.returncode != 0:
        _cycle_mod._stdio_info(f"! {check_id} failed (continuing loop)", fmt=stdio_format)
        return False
    return True


def _create_diagnostic_ticket(
    *,
    stdio_format: str = "human",
    project: Path,
    check_id: str,
    summary: str,
    cycle: int,
    queue_status: str,
    queue_name: str,
    priority: str,
    state_dir: Path,
) -> None:
    from koru import autonomous_cycle as _cycle_mod
    from koru.autonomous_diag_markers import diagnostic_marker_path

    state_dir.mkdir(parents=True, exist_ok=True)
    marker = diagnostic_marker_path(state_dir, check_id)
    if marker.exists():
        _cycle_mod._stdio_info(
            f"- diagnostic ticket marker exists for {check_id}, skipping create",
            fmt=stdio_format,
        )
        return
    title = f"[AUTO-DIAG] {check_id} needs attention"
    prompt = (
        f"{title} in cycle {cycle}. queue_status={queue_status}. "
        f"Check: {summary}. Investigate and fix regression, stale quality artifact, "
        "or broken diagnostic gate."
    )
    created = _cycle_mod.create_nl_task(
        project, prompt, queue_name=queue_name, priority=priority
    )
    marker.write_text(created.ticket_id, encoding="utf-8")
    _cycle_mod._stdio_info(
        f"+ created diagnostic ticket {created.ticket_id} for {check_id} (queue={queue_name})",
        fmt=stdio_format,
    )


def _clear_diagnostic_marker(state_dir: Path, check_id: str) -> None:
    from koru.autonomous_diag_markers import diagnostic_marker_path

    diagnostic_marker_path(state_dir, check_id).unlink(missing_ok=True)


def _read_wup_health(
    *,
    project: Path,
    state: AutoloopState,
    diagnostic_tickets: bool,
    ticket_queue: str,
    state_dir: Path,
) -> WupHealthResult:
    from koru import autonomous_cycle as _cycle_mod

    return _read_wup_health_impl(
        project=project,
        state=state,
        diagnostic_tickets=diagnostic_tickets,
        ticket_queue=ticket_queue,
        state_dir=state_dir,
        create_diagnostic_ticket=_cycle_mod._create_diagnostic_ticket,
    )


def _run_idle_diagnostics(
    *,
    stdio_format: str = "human",
    project: Path,
    profile: str,
    cycle: int,
    queue_status: str,
    diagnostic_tickets: bool,
    diagnostic_ticket_queue: str,
    diagnostic_ticket_priority: str,
    diagnostic_state_dir: Path,
    topology_integration: bool,
) -> DiagnosticResult:
    from koru import autonomous_cycle as _cycle_mod
    from koru import autonomous_diagnostics as diag

    def create_ticket(**kwargs: Any) -> None:
        _cycle_mod._create_diagnostic_ticket(stdio_format=stdio_format, **kwargs)

    return diag.run_idle_diagnostics(
        stdio_info=_cycle_mod._stdio_info,
        is_topology_enabled=_is_topology_enabled,
        run_command=_cycle_mod._run_command_check,
        clear_marker=_cycle_mod._clear_diagnostic_marker,
        create_ticket=create_ticket,
        make_result=lambda status, failed: DiagnosticResult(status=status, failed=failed),
        stdio_format=stdio_format,
        project=project,
        profile=profile,
        cycle=cycle,
        queue_status=queue_status,
        diagnostic_tickets=diagnostic_tickets,
        diagnostic_ticket_queue=diagnostic_ticket_queue,
        diagnostic_ticket_priority=diagnostic_ticket_priority,
        diagnostic_state_dir=diagnostic_state_dir,
        topology_integration=topology_integration,
    )


def _handle_diagnostics(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    idle_diagnostics: str,
    diagnostic_tickets: bool,
    diagnostic_ticket_queue: str,
    diagnostic_ticket_priority: str,
    diagnostic_state_dir: Path | None,
    wup_watch_enabled: bool,
    wup_diagnostic_tickets: bool,
    wup_ticket_queue: str,
    topology_integration: bool,
    _hp: callable,
    _emit: callable,
) -> tuple[DiagnosticResult, WupHealthResult]:
    from koru import autonomous_cycle as _cycle_mod

    diag_result = DiagnosticResult(status="skipped", failed=[])
    if queue_result.last_status == "idle" and idle_diagnostics not in {"off", "none"}:
        diag_result = _cycle_mod._run_idle_diagnostics(
            stdio_format="human",
            project=project,
            profile=idle_diagnostics,
            cycle=cycle,
            queue_status=queue_result.last_status,
            diagnostic_tickets=diagnostic_tickets,
            diagnostic_ticket_queue=diagnostic_ticket_queue,
            diagnostic_ticket_priority=diagnostic_ticket_priority,
            diagnostic_state_dir=diagnostic_state_dir or project / ".planfile/.koru/autoloop-diag",
            topology_integration=topology_integration,
        )

    wup_health = WupHealthResult(status="skipped", failing_services=[], new_events=0)
    if wup_watch_enabled:
        wup_health = _cycle_mod._read_wup_health(
            project=project,
            state=state,
            diagnostic_tickets=wup_diagnostic_tickets,
            ticket_queue=wup_ticket_queue,
            state_dir=diagnostic_state_dir or project / ".planfile/.koru/autoloop-diag",
        )
        if wup_health.status != "ok":
            _hp(
                f"koru autonomous: WUP health={wup_health.status} "
                f"failing={','.join(wup_health.failing_services) or '-'} "
                f"new_events={wup_health.new_events}",
            )
            if diag_result.status in {"skipped", "off", "ok"} and wup_health.status == "failed":
                diag_result = DiagnosticResult(status="failed", failed=["wup"])

    _emit(
        "WupHealthChanged",
        {
            "cycle": cycle,
            "watcher_enabled": wup_watch_enabled,
            "status": wup_health.status,
            "failing_services": list(wup_health.failing_services),
            "new_events": wup_health.new_events,
        },
    )
    _emit(
        "DiagnosticsCompleted",
        {"cycle": cycle, "status": diag_result.status, "failed": list(diag_result.failed)},
    )
    return diag_result, wup_health
