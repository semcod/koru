"""Query and command handlers delegating to koru/coru core."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HandlerResult:
    ok: bool
    output: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "output": self.output, "data": self.data, "error": self.error}


def run_query(payload: dict[str, Any], *, project_root: Path) -> HandlerResult:
    verb = str(payload["verb"]).upper()
    if verb == "QUERY_REPAIR_HISTORY":
        return _query_repair_history(payload, project_root=project_root)
    if verb == "QUERY_LANE_STATUS":
        return _query_lane_status(payload)
    if verb == "VALIDATE_LANE":
        return _validate_lane(payload)
    if verb == "RESOLVE":
        return _resolve(payload, project_root=project_root)
    return HandlerResult(ok=False, error=f"unknown query verb: {verb}")


def run_command(payload: dict[str, Any], *, project_root: Path) -> HandlerResult:
    verb = str(payload["verb"]).upper()
    if verb == "REPAIR_RUN":
        return _repair_run(payload, project_root=project_root)
    return HandlerResult(ok=False, error=f"unknown command verb: {verb}")


def _query_repair_history(payload: dict[str, Any], *, project_root: Path) -> HandlerResult:
    from coru.repair.query import RepairHistoryQuery

    limit = int(payload.get("limit", 20))
    code = payload.get("code")
    query = RepairHistoryQuery.for_project(project_root)
    if code:
        text = query.format_llm(limit=limit, code=str(code))
        data = json.loads(query.format_json(limit=limit, code=str(code)))
    else:
        text = query.format_llm(limit=limit)
        data = json.loads(query.format_json(limit=limit))
    return HandlerResult(ok=True, output=text, data={"cases": data, "store": str(query.store_path)})


def _query_lane_status(payload: dict[str, Any]) -> HandlerResult:
    from koruenv.lane import build_lane_environ, resolve_lane_socket, validate_ide, validate_instance

    ide = str(payload.get("ide", "auto"))
    instance = str(payload.get("instance", "default"))
    validate_ide(ide)
    validate_instance(instance)
    env = build_lane_environ(ide=ide, instance=instance)
    socket = resolve_lane_socket(ide=ide, instance=instance)
    data = {"ide": ide, "instance": instance, "socket": str(socket), "env": env}
    return HandlerResult(ok=True, output=json.dumps(data, indent=2, ensure_ascii=False), data=data)


def _validate_lane(payload: dict[str, Any]) -> HandlerResult:
    from koruenv.lane import validate_ide, validate_instance

    ide = str(payload.get("ide", "auto"))
    instance = str(payload.get("instance", "default"))
    validate_ide(ide)
    validate_instance(instance)
    return HandlerResult(ok=True, output="ok", data={"ide": ide, "instance": instance})


def _resolve(payload: dict[str, Any], *, project_root: Path) -> HandlerResult:
    from uri2koru.nlp2uri import nlp2uri

    prompt = str(payload.get("prompt", ""))
    hits = nlp2uri(prompt, project=str(project_root))
    data = [hit.to_dict() for hit in hits]
    return HandlerResult(
        ok=bool(hits),
        output=json.dumps(data, indent=2, ensure_ascii=False),
        data={"hits": data},
        error=None if hits else "no URI matches",
    )


def _repair_run(payload: dict[str, Any], *, project_root: Path) -> HandlerResult:
    from coru.repair.runtime import run_lane_repair

    ide = str(payload.get("ide", "auto"))
    instance = str(payload.get("instance", "default"))
    trigger = str(payload.get("trigger", "dsl2koru"))
    plan = run_lane_repair(
        ide,
        instance,
        trigger=trigger,
        project_root=project_root,
    )
    data = {
        "session_id": plan.session_id,
        "resolved": plan.resolved,
        "problems": [p.code for p in plan.problems],
        "attempts": [a.action_id for a in plan.attempts],
        "trigger": plan.trigger,
    }
    return HandlerResult(
        ok=plan.resolved or not plan.problems,
        output=json.dumps(data, indent=2, ensure_ascii=False),
        data=data,
        error=None if (plan.resolved or not plan.problems) else "repair session incomplete",
    )
