"""Append-only event store for repair sessions."""

from __future__ import annotations

import json
from pathlib import Path

from coru.repair.events import RepairEvent


class RepairEventStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    @classmethod
    def for_project(cls, project_root: Path) -> RepairEventStore:
        store_dir = (project_root / ".planfile" / ".koru").resolve()
        store_dir.mkdir(parents=True, exist_ok=True)
        return cls(store_dir / "repair-events.jsonl")

    def append(self, event: RepairEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def append_many(self, events: list[RepairEvent]) -> None:
        for event in events:
            self.append(event)

    def read_all(self) -> list[RepairEvent]:
        if not self._path.is_file():
            return []
        events: list[RepairEvent] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(raw, dict):
                events.append(RepairEvent.from_dict(raw))
        return events

    def read_recent(self, *, limit: int = 50) -> list[RepairEvent]:
        all_events = self.read_all()
        if limit <= 0:
            return all_events
        return all_events[-limit:]
