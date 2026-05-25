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
    event = obs_event(corr=corr, component=component, kind="autopilot.intent", **data)
    record_obs_event(project, event)
    return event


def emit_decision(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    event = obs_event(corr=corr, component=component, kind="autopilot.route.decision", **data)
    record_obs_event(project, event)
    return event


def emit_action(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    event = obs_event(corr=corr, component=component, kind="autopilot.drive.requested", **data)
    record_obs_event(project, event)
    return event


def emit_phase(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    event = obs_event(corr=corr, component=component, kind="autopilot.drive.phase", **data)
    record_obs_event(project, event)
    return event


def emit_verify(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    event = obs_event(corr=corr, component=component, kind="autopilot.drive.verified", **data)
    record_obs_event(project, event)
    return event


def emit_failure(
    project: Path | None, *, corr: str, component: str = "autopilot", **data: Any
) -> KoruObsEvent:
    event = obs_event(
        corr=corr,
        component=component,
        kind="autopilot.drive.failed",
        severity="error",
        **data,
    )
    record_obs_event(project, event)
    return event


def emit_blocker(
    project: Path | None, *, corr: str, component: str = "autonomy", **data: Any
) -> KoruObsEvent:
    event = obs_event(corr=corr, component=component, kind="autonomy.blocker", **data)
    record_obs_event(project, event)
    return event


def emit_next(
    project: Path | None, *, corr: str, component: str = "autonomy", **data: Any
) -> KoruObsEvent:
    event = obs_event(corr=corr, component=component, kind="autonomy.next", **data)
    record_obs_event(project, event)
    return event


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
