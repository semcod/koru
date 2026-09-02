"""Push Planfile ticket changes to configured external trackers synchronously.

Koru never talks to GitHub/Jira/GitLab directly. After a local Planfile
mutation it delegates to Planfile's sync layer so remote issues reflect
living status and new backlog items immediately.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from koru.policy import policy_path

_logger = logging.getLogger(__name__)

_REMOTE_INTEGRATIONS = frozenset({"github", "gitlab", "jira", "onedev"})


@dataclass(frozen=True)
class PlanfileSyncConfig:
    enabled: bool = True
    integrations: tuple[str, ...] = ()
    direction: str = "to"
    on_create: bool = True
    on_update: bool = True


@dataclass(frozen=True)
class PlanfileSyncResult:
    ok: bool
    integrations: tuple[str, ...]
    errors: tuple[str, ...] = ()


def _env_disabled() -> bool:
    value = os.environ.get("KORU_PLANFILE_SYNC", "").strip().lower()
    return value in {"0", "false", "no", "off"}


def _load_raw_policy(project: Path) -> dict[str, Any]:
    path = policy_path(project)
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    return raw if isinstance(raw, dict) else {}


def load_planfile_sync_config(project: Path) -> PlanfileSyncConfig:
    """Resolve sync policy from ``.planfile/.koru/policy.yaml``."""
    if _env_disabled():
        return PlanfileSyncConfig(enabled=False)

    raw = _load_raw_policy(project)
    section = raw.get("planfile_sync")
    if section is False:
        return PlanfileSyncConfig(enabled=False)
    if not isinstance(section, dict):
        return PlanfileSyncConfig()

    def _bool(key: str, default: bool) -> bool:
        value = section.get(key)
        return value if isinstance(value, bool) else default

    integrations_raw = section.get("integrations")
    integrations: tuple[str, ...] = ()
    if isinstance(integrations_raw, list):
        integrations = tuple(
            str(item).strip()
            for item in integrations_raw
            if isinstance(item, str) and str(item).strip()
        )

    direction = section.get("direction")
    return PlanfileSyncConfig(
        enabled=_bool("enabled", True),
        integrations=integrations,
        direction=str(direction).strip() if isinstance(direction, str) and direction.strip() else "to",
        on_create=_bool("on_create", True),
        on_update=_bool("on_update", True),
    )


def configured_remote_integrations(project: Path) -> tuple[str, ...]:
    """Return validated non-markdown Planfile integrations for *project*."""
    try:
        from planfile.integrations.config import IntegrationConfig
    except ImportError:
        return ()

    config = IntegrationConfig(str(project.resolve()))
    config.load_configs()
    names = list(config.config.get("integrations", {}).keys())
    remote = [
        name
        for name in names
        if name in _REMOTE_INTEGRATIONS and config.validate_integration(name)
    ]
    return tuple(remote)


def resolve_sync_integrations(project: Path, config: PlanfileSyncConfig | None = None) -> tuple[str, ...]:
    """Pick integration backends to sync for *project*."""
    resolved = config or load_planfile_sync_config(project)
    if resolved.integrations:
        return resolved.integrations
    return configured_remote_integrations(project)


def stamp_ticket_integrations(ticket: dict[str, Any], integrations: Sequence[str]) -> bool:
    """Ensure *ticket* is routed to every configured backend."""
    names = [str(name).strip() for name in integrations if str(name).strip()]
    if not names:
        return False

    current = ticket.get("integration")
    merged: list[str]
    if isinstance(current, list):
        merged = list(dict.fromkeys([*(str(item) for item in current), *names]))
    elif current:
        merged = list(dict.fromkeys([str(current), *names]))
    else:
        merged = list(dict.fromkeys(names))

    if ticket.get("integration") == merged:
        return False
    ticket["integration"] = merged
    return True


def _persist_ticket_integration_stamp(
    project: Path,
    ticket_id: str,
    integrations: Sequence[str],
) -> None:
    if not integrations:
        return
    try:
        from planfile.core.store import PlanfileStore
    except ImportError:
        return

    store = PlanfileStore(str(project.resolve()))
    if not store.is_initialized():
        return

    sprint = store.load_sprint("current") or {"tickets": {}}
    ticket = sprint.get("tickets", {}).get(ticket_id)
    if not isinstance(ticket, dict):
        backlog = store.load_backlog() or {"tickets": {}}
        ticket = backlog.get("tickets", {}).get(ticket_id)
        if not isinstance(ticket, dict):
            return
        if stamp_ticket_integrations(ticket, integrations):
            store.save_backlog(backlog)
        return

    if stamp_ticket_integrations(ticket, integrations):
        store.save_sprint("current", sprint)


def _sync_integration(
    integration: str,
    project: Path,
    *,
    direction: str,
    dry_run: bool,
) -> str | None:
    try:
        from planfile.cli.groups.sync.core import sync_integration
    except ImportError as exc:
        return f"{integration}: planfile sync unavailable ({exc})"

    try:
        sync_integration(
            integration,
            str(project.resolve()),
            dry_run,
            direction,
            show_header=False,
        )
    except SystemExit as exc:
        code = int(exc.code) if isinstance(exc.code, int) else 1
        if code:
            return f"{integration}: sync exited {code}"
    except Exception as exc:  # noqa: BLE001 — best-effort remote publication
        return f"{integration}: {exc}"
    return None


def sync_planfile_integrations(
    project: Path,
    *,
    integrations: Sequence[str] | None = None,
    direction: str | None = None,
    dry_run: bool = False,
    ticket_ids: Sequence[str] | None = None,
) -> PlanfileSyncResult:
    """Synchronously publish local Planfile tickets to external trackers."""
    project = project.resolve()
    config = load_planfile_sync_config(project)
    if not config.enabled:
        return PlanfileSyncResult(ok=True, integrations=())

    targets = tuple(integrations or resolve_sync_integrations(project, config))
    if not targets:
        return PlanfileSyncResult(ok=True, integrations=())

    if ticket_ids:
        for ticket_id in ticket_ids:
            _persist_ticket_integration_stamp(project, str(ticket_id), targets)

    sync_direction = direction or config.direction
    errors: list[str] = []
    for integration in targets:
        error = _sync_integration(integration, project, direction=sync_direction, dry_run=dry_run)
        if error:
            errors.append(error)
            _logger.warning("planfile sync failed project=%s %s", project, error)

    return PlanfileSyncResult(
        ok=not errors,
        integrations=targets,
        errors=tuple(errors),
    )


def sync_after_ticket_create(project: Path, ticket_id: str) -> PlanfileSyncResult:
    config = load_planfile_sync_config(project)
    if not config.enabled or not config.on_create:
        return PlanfileSyncResult(ok=True, integrations=())
    return sync_planfile_integrations(project, ticket_ids=[ticket_id])


def sync_after_ticket_update(project: Path, ticket_id: str) -> PlanfileSyncResult:
    config = load_planfile_sync_config(project)
    if not config.enabled or not config.on_update:
        return PlanfileSyncResult(ok=True, integrations=())
    return sync_planfile_integrations(project, ticket_ids=[ticket_id])


__all__ = [
    "PlanfileSyncConfig",
    "PlanfileSyncResult",
    "configured_remote_integrations",
    "load_planfile_sync_config",
    "resolve_sync_integrations",
    "stamp_ticket_integrations",
    "sync_after_ticket_create",
    "sync_after_ticket_update",
    "sync_planfile_integrations",
]
