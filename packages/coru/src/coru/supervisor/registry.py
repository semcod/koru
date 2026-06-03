"""Persistent lane registry with file locking."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from coru.supervisor.editor_cli import resolve_editor_cli
from coru.supervisor.models import LaneHealth, LaneRecord, SupervisorRegistry
from coru.supervisor.paths import registry_path, state_dir
from coru.supervisor.socket_path import socket_path_for_instance


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_state_dir() -> Path:
    root = state_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextlib.contextmanager
def _registry_lock(path: Path, *, exclusive: bool) -> Iterator[None]:
    _ensure_state_dir()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_registry(*, path: Path | None = None) -> SupervisorRegistry:
    target = path or registry_path()
    if not target.is_file():
        return SupervisorRegistry()
    with _registry_lock(target, exclusive=False):
        raw = target.read_text(encoding="utf-8").strip()
    if not raw:
        return SupervisorRegistry()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return SupervisorRegistry()
    return SupervisorRegistry.from_dict(payload)


def save_registry(registry: SupervisorRegistry, *, path: Path | None = None) -> None:
    target = path or registry_path()
    registry.updated_at = _iso_now()
    payload = json.dumps(registry.to_dict(), indent=2, sort_keys=True) + "\n"
    with _registry_lock(target, exclusive=True):
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)


def register_lane(
    *,
    ide: str,
    instance: str,
    project: str | None = None,
    set_active: bool = False,
    editor_cli: str | None = None,
    path: Path | None = None,
) -> LaneRecord:
    registry = load_registry(path=path)
    now = _iso_now()
    existing = registry.lanes.get(instance)
    resolved_project = project
    if resolved_project:
        project_path = Path(resolved_project).expanduser()
        if not project_path.is_dir():
            raise FileNotFoundError(f"project directory does not exist: {project_path}")
        resolved_project = str(project_path.resolve())
    elif existing and existing.project:
        resolved_project = existing.project
    resolved_cli = editor_cli or (existing.editor_cli if existing else None) or resolve_editor_cli(ide)
    record = LaneRecord(
        ide=ide,
        instance=instance,
        socket_path=str(socket_path_for_instance(instance)),
        editor_cli=resolved_cli,
        project=resolved_project,
        daemon_desired=existing.daemon_desired if existing else True,
        health=existing.health if existing else LaneHealth(),
        created_at=existing.created_at if existing and existing.created_at else now,
        updated_at=now,
    )
    registry.lanes[instance] = record
    if set_active or not registry.active_lane:
        registry.active_lane = instance
    save_registry(registry, path=path)
    return record


def set_active_lane(instance: str, *, path: Path | None = None) -> LaneRecord:
    registry = load_registry(path=path)
    record = registry.lanes.get(instance)
    if record is None:
        raise KeyError(f"unknown lane instance: {instance}")
    registry.active_lane = instance
    record.updated_at = _iso_now()
    save_registry(registry, path=path)
    return record


def remove_lane(instance: str, *, path: Path | None = None) -> bool:
    registry = load_registry(path=path)
    if instance not in registry.lanes:
        return False
    registry.lanes.pop(instance, None)
    if registry.active_lane == instance:
        registry.active_lane = next(iter(registry.lanes), None)
    save_registry(registry, path=path)
    return True


def update_lane_health(
    instance: str,
    health: LaneHealth,
    *,
    path: Path | None = None,
) -> None:
    registry = load_registry(path=path)
    record = registry.lanes.get(instance)
    if record is None:
        return
    record.health = health
    record.updated_at = _iso_now()
    save_registry(registry, path=path)


def active_lane_pair(*, path: Path | None = None) -> tuple[str, str] | None:
    registry = load_registry(path=path)
    record = registry.active_record()
    if record is None:
        return None
    return record.ide, record.instance
