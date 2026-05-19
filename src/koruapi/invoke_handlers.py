"""Per-integration invoke handlers for koruapi."""

from __future__ import annotations

import json
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import Any


class InvokeError(RuntimeError):
    pass


IntegrationHandler = Callable[[Path, str, dict[str, Any]], dict[str, Any]]


def _handle_context_build(project: Path, _method: str, payload: dict[str, Any]) -> dict[str, Any]:
    from koru.context import build_context

    ctx = build_context(
        project=project,
        ticket_id=payload.get("ticket_id"),
        queue_name=payload.get("queue_name", "default"),
    )
    return {"ok": True, "context": ctx}


def _handle_doctor_run(project: Path, _method: str, _payload: dict[str, Any]) -> dict[str, Any]:
    from koru.doctor import run_diagnostics

    report = run_diagnostics(project)
    return {"ok": not report.has_failures, "report": report.to_dict()}


def _handle_scan_apply(project: Path, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    from koru.scan import run_scan

    result = run_scan(
        project,
        apply=method != "dry_run",
        include_semcod_artifacts=bool(payload.get("semcod_artifacts", False)),
    )
    return {"ok": True, "result": result.to_dict()}


def _handle_queue_loop(project: Path, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    from koru.queue import run_planfile_queue_loop
    from koru.queue.runners import run_api_request, run_llm_request, run_process, run_shell_command

    loop_result = run_planfile_queue_loop(
        project=project,
        actor=str(payload.get("actor", "koru-api")),
        queue_name=payload.get("queue_name"),
        max_iterations=int(payload.get("max_iterations", 1 if method == "once" else 50)),
        planfile_runner=run_process,
        shell_runner=run_shell_command,
        api_runner=run_api_request,
        llm_runner=run_llm_request,
    )
    return {"ok": True, "summary": loop_result.summary(), "last_status": loop_result.last_status}


def _handle_autopilot_status(
    _project: Path, _method: str, _payload: dict[str, Any]
) -> dict[str, Any]:
    from koru.ide_client import build_ide_client

    client = build_ide_client()
    if not client.is_running():
        return {"ok": False, "running": False, "message": "autopilot daemon not running"}
    status = client.status()
    return {"ok": True, "running": True, "status": status}


def _handle_autopilot_drive(
    _project: Path, _method: str, payload: dict[str, Any]
) -> dict[str, Any]:
    from koru.ide_client import build_ide_client

    text = str(payload.get("text") or payload.get("prompt") or "")
    if not text.strip():
        raise InvokeError("autopilot.drive requires body.text or body.prompt")
    client = build_ide_client()
    if not client.is_running():
        raise InvokeError("autopilot daemon not running")
    reply = client.drive(
        text,
        submit=bool(payload.get("submit", True)),
        ide=str(payload.get("ide", "auto")),
        require_plugin=bool(payload.get("require_plugin", False)),
    )
    return {"ok": bool(reply.get("ok", True)), "reply": reply}


def _handle_dsl_to_library(_project: Path, _method: str, payload: dict[str, Any]) -> dict[str, Any]:
    from korudsl import library_from_any

    raw = payload.get("dsl") or payload.get("text") or ""
    lib = library_from_any(str(raw), kind="dsl")
    return {"ok": True, "library": lib}


def _handle_dsl_to_dsl(_project: Path, _method: str, payload: dict[str, Any]) -> dict[str, Any]:
    from korudsl import library_from_any, library_to_any

    lib = library_from_any(payload.get("library") or payload, kind="library")
    return {"ok": True, "dsl": library_to_any(lib, fmt="dsl")}


def _handle_dsl_roundtrip(_project: Path, _method: str, payload: dict[str, Any]) -> dict[str, Any]:
    from korudsl import dsl_roundtrip_report

    raw = str(payload.get("dsl") or payload.get("text") or "")
    report = dsl_roundtrip_report(raw)
    return {"ok": bool(report.get("ok")), "report": report}


def _handle_topology_read(project: Path, _method: str, _payload: dict[str, Any]) -> dict[str, Any]:
    from koru.topology import load_topology

    return {"ok": True, "topology": load_topology(project)}


def _handle_gate_regix(project: Path, _method: str, payload: dict[str, Any]) -> dict[str, Any]:
    from koru.queue.runners import run_process

    cmd = payload.get("command") or ["task", "quality:regix:local"]
    cmd_list = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
    result = run_process(cmd_list, project)
    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _handle_planfile_tickets(
    project: Path, _method: str, payload: dict[str, Any]
) -> dict[str, Any]:
    from koru.queue.runners import run_process
    from koru.queue.ticket import planfile_command

    status = str(payload.get("status", "open"))
    result = planfile_command(
        project,
        ["ticket", "list", "--status", status, "--format", "json"],
        runner=run_process,
    )
    if result.returncode != 0:
        return {"ok": False, "stderr": result.stderr, "stdout": result.stdout}
    try:
        tickets = json.loads((result.stdout or "").strip() or "[]")
    except json.JSONDecodeError:
        tickets = []
    return {"ok": True, "tickets": tickets}


def _handle_mcp_list_tickets(
    project: Path, _method: str, payload: dict[str, Any]
) -> dict[str, Any]:
    from koruapi.mcp_server import tool_list_tickets

    return tool_list_tickets({"project": str(project), **payload})


def _handle_mcp_run_ticket(project: Path, _method: str, payload: dict[str, Any]) -> dict[str, Any]:
    from koruapi.mcp_server import tool_run_ticket

    return tool_run_ticket({"project": str(project), **payload})


def _handle_mcp_quality_gates(
    project: Path, _method: str, payload: dict[str, Any]
) -> dict[str, Any]:
    from koruapi.mcp_server import tool_run_quality_gates

    return tool_run_quality_gates({"project": str(project), **payload})


INTEGRATION_HANDLERS: dict[str, IntegrationHandler] = {
    "context.build": _handle_context_build,
    "doctor.run": _handle_doctor_run,
    "scan.apply": _handle_scan_apply,
    "queue.loop": _handle_queue_loop,
    "autopilot.status": _handle_autopilot_status,
    "autopilot.drive": _handle_autopilot_drive,
    "dsl.to_library": _handle_dsl_to_library,
    "dsl.to_dsl": _handle_dsl_to_dsl,
    "dsl.roundtrip": _handle_dsl_roundtrip,
    "topology.read": _handle_topology_read,
    "gate.regix": _handle_gate_regix,
    "planfile.tickets": _handle_planfile_tickets,
    "mcp.list_tickets": _handle_mcp_list_tickets,
    "mcp.run_ticket": _handle_mcp_run_ticket,
    "mcp.quality_gates": _handle_mcp_quality_gates,
}
