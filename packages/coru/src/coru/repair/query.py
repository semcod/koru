"""CQRS read side: query repair history for humans and LLMs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from coru.repair.domain import RepairCaseSummary, RepairProblem
from coru.repair.events import RepairEvent, aggregate_id_for
from coru.repair.projector import format_history_llm, project_repair_cases
from coru.repair.store import RepairEventStore


class RepairHistoryQuery:
    def __init__(self, store: RepairEventStore) -> None:
        self._store = store

    @classmethod
    def for_project(cls, project_root: Path) -> RepairHistoryQuery:
        store = RepairEventStore.for_project(project_root)
        return cls(store)

    @property
    def store_path(self) -> Path:
        return self._store.path

    def cases(self, *, limit: int = 50) -> list[RepairCaseSummary]:
        events = self._store.read_all()
        cases = project_repair_cases(events)
        if limit <= 0:
            return cases
        return cases[-limit:]

    def cases_for_lane(self, ide: str, instance: str, *, limit: int = 20) -> list[RepairCaseSummary]:
        aggregate = aggregate_id_for(ide, instance)
        events = [
            event
            for event in self._store.read_all()
            if event.aggregate_id == aggregate or event.payload.get("instance") == instance
        ]
        cases = project_repair_cases(events)
        if limit <= 0:
            return cases
        return cases[-limit:]

    def cases_matching_code(self, code: str, *, limit: int = 20) -> list[RepairCaseSummary]:
        needle = code.strip()
        matched = [case for case in self.cases(limit=0) if needle in case.problem_codes]
        if limit <= 0:
            return matched
        return matched[-limit:]

    def format_llm(self, *, limit: int = 20, code: str | None = None) -> str:
        if code:
            cases = self.cases_matching_code(code, limit=limit)
        else:
            cases = self.cases(limit=limit)
        return format_history_llm(cases, limit=limit)

    def format_json(self, *, limit: int = 20, code: str | None = None) -> str:
        if code:
            cases = self.cases_matching_code(code, limit=limit)
        else:
            cases = self.cases(limit=limit)
        payload = [asdict(case) for case in cases]
        return json.dumps(payload, indent=2, ensure_ascii=False)


def problems_to_payload(problems: list[RepairProblem]) -> list[dict[str, object]]:
    return [
        {
            "code": p.code,
            "severity": p.severity,
            "message": p.message,
            "fix_hint": p.fix_hint,
            "context": dict(p.context),
        }
        for p in problems
    ]
