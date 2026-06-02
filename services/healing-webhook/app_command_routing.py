from __future__ import annotations

from collections.abc import Callable
from logging import Logger
import time
from typing import Any


def route_alertmanager_payload(
    payload: dict[str, Any],
    *,
    resolve_strategy: Callable[[str], tuple[Callable[[str, dict[str, Any]], dict[str, Any]], str]],
    create_planfile_ticket: Callable[[dict[str, Any]], dict[str, Any]],
    alerts_counter: Any,
    log: Logger,
) -> dict[str, Any]:
    """Route Alertmanager alerts through healing strategies and ticketing."""
    results: list[dict[str, Any]] = []
    for alert in payload.get("alerts", []):
        labels = alert.get("labels", {})
        severity = labels.get("severity", "info")
        component = labels.get("component", "unknown")
        strategy_name = labels.get("healing_strategy", "annotate")
        status = alert.get("status", "firing")
        alerts_counter.labels(source="alertmanager", severity=severity).inc()
        if status != "firing":
            strategy_name = "annotate"
        strategy, effective_strategy_name = resolve_strategy(strategy_name)
        log.info(
            "alert %s/%s -> %s",
            severity,
            labels.get("alertname"),
            effective_strategy_name,
        )
        strategy_result = strategy(
            component,
            {"labels": labels, "annotations": alert.get("annotations", {})},
        )
        ticket_result: dict[str, Any] = {"skipped": "severity_below_threshold"}
        if status == "firing" and severity in {"error", "critical"}:
            ticket_result = create_planfile_ticket(alert)
        results.append({"strategy": strategy_result, "ticket": ticket_result})
    return {"received": len(payload.get("alerts", [])), "results": results}


def route_probe_failure_payload(
    payload: dict[str, Any],
    *,
    heal_redsl_improve: Callable[[str, dict[str, Any]], dict[str, Any]],
    heal_redsl_gate: Callable[[str, dict[str, Any]], dict[str, Any]],
    create_planfile_ticket: Callable[[dict[str, Any]], dict[str, Any]],
    alerts_counter: Any,
    enable_llm_autofix: bool,
    log: Logger,
) -> dict[str, Any]:
    """Route probe-failure payload through strategy and consolidated ticketing."""
    alerts_counter.labels(source="testql-watchdog", severity="error").inc()
    failures = payload.get("failures", [])
    log.info("probe-failure from %s - %d failures", payload.get("source"), len(failures))
    total = payload.get("total") or max(len(failures), 1)
    ratio = len(failures) / total if total else 0.0
    if ratio >= 0.5 and enable_llm_autofix:
        result = heal_redsl_improve("backend", {"failures": failures, "ratio": ratio})
    else:
        result = heal_redsl_gate("backend", {"failures": failures, "ratio": ratio})

    synthetic_alert = {
        "labels": {
            "alertname": "TestQLProbeFailure",
            "severity": "critical" if ratio >= 0.5 else "error",
            "component": "backend",
            "instance": (failures[0].get("endpoint") if failures else "multiple"),
        },
        "annotations": {
            "summary": f"{len(failures)} TestQL probe(s) failed out of {total} ({ratio:.0%}).",
            "observed": f"{len(failures)}/{total} endpoints failing",
        },
        "failures": failures,
        "startsAt": str(time.time()),
    }
    ticket_result = create_planfile_ticket(synthetic_alert)
    return {"failures": len(failures), "result": result, "ticket": ticket_result}
