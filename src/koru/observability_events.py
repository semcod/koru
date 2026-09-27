"""Domain helper constructors for Koru observability events."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.observability_dsl import KoruObsEvent
from koru.observability_writer import try_write_observability_event


def obs_event(
    *,
    corr: str,
    component: str,
    kind: str,
    session: str | None = None,
    cycle: int | None = None,
    ticket: str | None = None,
    actor: str | None = None,
    severity: str | None = None,
    **data: Any,
) -> KoruObsEvent:
    return KoruObsEvent(
        corr=corr,
        component=component,
        kind=kind,
        session=session,
        cycle=cycle,
        ticket=ticket,
        actor=actor,
        severity=severity,
        data={key: value for key, value in data.items() if value is not None},
    )


def record_obs_event(project: Path | None, event: KoruObsEvent) -> None:
    try_write_observability_event(event, project=project)


def emit_intent(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    intent_event = obs_event(corr=corr, component=component, kind="autopilot.intent", **data)
    record_obs_event(project, intent_event)
    return intent_event


def emit_decision(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    decision_event = obs_event(corr=corr, component=component, kind="autopilot.route.decision", **data)
    record_obs_event(project, decision_event)
    return decision_event


def emit_action(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    action_event = obs_event(corr=corr, component=component, kind="autopilot.drive.requested", **data)
    record_obs_event(project, action_event)
    return action_event


def emit_phase(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    phase_event = obs_event(corr=corr, component=component, kind="autopilot.drive.phase", **data)
    record_obs_event(project, phase_event)
    return phase_event


def emit_verify(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    verified_event = obs_event(corr=corr, component=component, kind="autopilot.drive.verified", **data)
    record_obs_event(project, verified_event)
    return verified_event


def emit_failure(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    failure_event = obs_event(
        corr=corr,
        component=component,
        kind="autopilot.drive.failed",
        severity="error",
        **data,
    )
    record_obs_event(project, failure_event)
    return failure_event


def emit_blocker(
    project: Path | None, *, corr: str, component: str = "autonomy", **data: Any
) -> KoruObsEvent:
    blocker_event = obs_event(corr=corr, component=component, kind="autonomy.blocker", **data)
    record_obs_event(project, blocker_event)
    return blocker_event


def emit_next(
    project: Path | None, *, corr: str, component: str = "autonomy", **data: Any
) -> KoruObsEvent:
    next_event = obs_event(corr=corr, component=component, kind="autonomy.next", **data)
    record_obs_event(project, next_event)
    return next_event


__all__ = [
    "emit_action",
    "emit_blocker",
    "emit_decision",
    "emit_failure",
    "emit_intent",
    "emit_next",
    "emit_phase",
    "emit_verify",
    "obs_event",
    "record_obs_event",
]
