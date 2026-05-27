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


def _handle_ide_commands(_project: Path, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    from koruide.command_catalog import build_ide_command_catalog, command_catalog_for_llm

    ide = payload.get("ide")
    ide_arg = None if ide in (None, "", "all") else str(ide)
    for_llm = bool(payload.get("for_llm", method == "llm"))
    catalog = command_catalog_for_llm(ide_arg) if for_llm else build_ide_command_catalog(ide_arg)
    return {"ok": True, "catalog": catalog}


def _handle_ide_scenario_schema(
    _project: Path, _method: str, _payload: dict[str, Any]
) -> dict[str, Any]:
    from koruide.command_scenario import ide_command_scenario_schema

    return {"ok": True, "schema": ide_command_scenario_schema()}


def _handle_ide_scenario_validate(
    _project: Path, _method: str, payload: dict[str, Any]
) -> dict[str, Any]:
    from koruide.command_scenario import validate_ide_command_scenario

    scenario = payload.get("scenario") or payload
    if not isinstance(scenario, dict):
        raise InvokeError("ide.scenario_validate requires body.scenario object")
    result = validate_ide_command_scenario(scenario)
    return {"ok": result.ok, "validation": result.to_dict()}


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


def _handle_lane_plan(project: Path, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Handle lane.plan integration - generate task plan via lane CLI."""
    from koru.queue.runners import run_process

    extra_context = payload.get("extra_context", "")
    sync_todo = payload.get("sync_todo", False)
    sync_planfile = payload.get("sync_planfile", False)
    export_yaml = payload.get("export_yaml", False)

    cmd = ["lane", "tickets", str(project)]

    if extra_context:
        cmd.extend(["--extra-context", extra_context])
    if sync_todo:
        cmd.append("--sync-todo")
    if sync_planfile:
        cmd.append("--sync-planfile")
    if export_yaml:
        cmd.append("--export-yaml")

    result = run_process(cmd, project)

    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "method": method,
        "sync_todo": sync_todo,
        "sync_planfile": sync_planfile,
        "export_yaml": export_yaml,
        "koru_aware": koru_aware,
    }


def _handle_tagi_analyze(project: Path, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Handle tagi.analyze integration - analyze changes using Tagi."""
    try:
        from koru.tagi_integration import analyze_project_changes
        return analyze_project_changes(project)
    except ImportError:
        return {
            "ok": False,
            "error": "Tagi integration not available",
            "message": "Install tagi: pip install tagi"
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


def _handle_tagi_deploy(project: Path, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Handle tagi.deploy integration - deploy changes using Tagi."""
    try:
        from koru.tagi_integration import TagiIntegration
        tagi = TagiIntegration(project)
        
        if not tagi.is_available():
            return {
                "ok": False,
                "error": "Tagi not available",
                "message": "Install tagi: pip install tagi"
            }
        
        dry_run = payload.get("dry_run", False)
        deployment_plan = tagi.get_deployment_plan()
        
        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "deployment_plan": deployment_plan
            }
        
        # Execute deployment
        success = True
        deployed_groups = []
        
        for group in deployment_plan.get("deployment_groups", []):
            group_name = group.get("name", "")
            if group_name:
                group_success = tagi.commit_changes(group_name)
                if group_success:
                    deployed_groups.append(group_name)
                else:
                    success = False
                    break
        
        return {
            "ok": success,
            "deployed_groups": deployed_groups,
            "deployment_plan": deployment_plan
        }
        
    except ImportError:
        return {
            "ok": False,
            "error": "Tagi integration not available",
            "message": "Install tagi: pip install tagi"
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


def _handle_tagi_auto(project: Path, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Handle tagi.auto integration - auto-commit changes using Tagi."""
    try:
        from koru.tagi_integration import auto_commit_all_changes
        message = payload.get("message", "Auto-commit changes via Koru")
        dry_run = payload.get("dry_run", False)
        
        if dry_run:
            from koru.tagi_integration import TagiIntegration
            tagi = TagiIntegration(project)
            analysis = tagi.analyze_priorities()
            return {
                "ok": True,
                "dry_run": True,
                "analysis": {
                    "changes": len(analysis.changes),
                    "groups": len(analysis.groups),
                    "priority_order": analysis.priority_order,
                    "recommendations": analysis.recommendations
                }
            }
        
        success = auto_commit_all_changes(project, message)
        return {
            "ok": success,
            "message": message
        }
        
    except ImportError:
        return {
            "ok": False,
            "error": "Tagi integration not available",
            "message": "Install tagi: pip install tagi"
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


INTEGRATION_HANDLERS: dict[str, IntegrationHandler] = {
    "context.build": _handle_context_build,
    "doctor.run": _handle_doctor_run,
    "scan.apply": _handle_scan_apply,
    "queue.loop": _handle_queue_loop,
    "autopilot.status": _handle_autopilot_status,
    "autopilot.drive": _handle_autopilot_drive,
    "ide.commands": _handle_ide_commands,
    "ide.scenario_schema": _handle_ide_scenario_schema,
    "ide.scenario_validate": _handle_ide_scenario_validate,
    "dsl.to_library": _handle_dsl_to_library,
    "dsl.to_dsl": _handle_dsl_to_dsl,
    "dsl.roundtrip": _handle_dsl_roundtrip,
    "topology.read": _handle_topology_read,
    "gate.regix": _handle_gate_regix,
    "planfile.tickets": _handle_planfile_tickets,
    "mcp.list_tickets": _handle_mcp_list_tickets,
    "mcp.run_ticket": _handle_mcp_run_ticket,
    "mcp.quality_gates": _handle_mcp_quality_gates,
    "lane.plan": _handle_lane_plan,
    "tagi.analyze": _handle_tagi_analyze,
    "tagi.deploy": _handle_tagi_deploy,
    "tagi.auto": _handle_tagi_auto,
}
