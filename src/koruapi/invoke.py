"""Invoke koru integrations by id (used by HTTP API and CLI)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .integrations import get_integration


class InvokeError(RuntimeError):
    pass


def invoke_integration(
    integration_id: str,
    *,
    project: Path,
    method: str = "run",
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run an integration and return a JSON-serializable result."""
    spec = get_integration(integration_id)
    if spec is None:
        raise InvokeError(f"unknown integration: {integration_id!r}")

    payload = body or {}
    project = project.resolve()

    if integration_id == "context.build":
        from koru.context import build_context

        ctx = build_context(
            project=project,
            ticket_id=payload.get("ticket_id"),
            queue_name=payload.get("queue_name", "default"),
        )
        return {"ok": True, "context": ctx}

    if integration_id == "doctor.run":
        from koru.doctor import run_diagnostics

        report = run_diagnostics(project)
        return {"ok": not report.has_failures, "report": report.to_dict()}

    if integration_id == "scan.apply":
        from koru.scan import run_scan

        result = run_scan(
            project,
            apply=method != "dry_run",
            include_semcod_artifacts=bool(payload.get("semcod_artifacts", False)),
        )
        return {"ok": True, "result": result.to_dict()}

    if integration_id == "queue.loop":
        from koru.queue import run_planfile_queue_loop
        from koru.queue.runners import run_process, run_shell_command
        from koru.queue.runners import run_api_request, run_llm_request

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

    if integration_id == "autopilot.status":
        from koru.ide_client import build_ide_client

        client = build_ide_client()
        if not client.is_running():
            return {"ok": False, "running": False, "message": "autopilot daemon not running"}
        status = client.status()
        return {"ok": True, "running": True, "status": status}

    if integration_id == "autopilot.drive":
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

    if integration_id == "dsl.to_library":
        from korudsl import library_from_any

        raw = payload.get("dsl") or payload.get("text") or ""
        lib = library_from_any(str(raw), kind="dsl")
        return {"ok": True, "library": lib}

    if integration_id == "dsl.to_dsl":
        from korudsl import library_from_any, library_to_any

        lib = library_from_any(payload.get("library") or payload, kind="library")
        return {"ok": True, "dsl": library_to_any(lib, fmt="dsl")}

    if integration_id == "dsl.roundtrip":
        from korudsl import dsl_roundtrip_report

        raw = str(payload.get("dsl") or payload.get("text") or "")
        report = dsl_roundtrip_report(raw)
        return {"ok": bool(report.get("ok")), "report": report}

    if integration_id == "topology.read":
        from koru.topology import load_topology

        return {"ok": True, "topology": load_topology(project)}

    if integration_id == "gate.regix":
        from koru.queue.runners import run_process

        cmd = payload.get("command") or ["task", "quality:regix:local"]
        if isinstance(cmd, str):
            import shlex

            cmd_list = shlex.split(cmd)
        else:
            cmd_list = list(cmd)
        result = run_process(cmd_list, project)
        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    if integration_id == "planfile.tickets":
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

    if integration_id == "mcp.list_tickets":
        from koruapi.mcp_server import tool_list_tickets

        return tool_list_tickets({"project": str(project), **payload})

    if integration_id == "mcp.run_ticket":
        from koruapi.mcp_server import tool_run_ticket

        return tool_run_ticket({"project": str(project), **payload})

    if integration_id == "mcp.quality_gates":
        from koruapi.mcp_server import tool_run_quality_gates

        return tool_run_quality_gates({"project": str(project), **payload})

    raise InvokeError(
        f"integration {integration_id!r} is catalogued but not wired for method={method!r}"
    )
