from __future__ import annotations

import json
from pathlib import Path

from coru.repair import (
    RepairProblem,
    RepairService,
    RunRepairSessionCommand,
    collect_problems_from_drive_result,
    run_repair_with_events,
)
from coru.repair.query import RepairHistoryQuery
from coru.repair.store import RepairEventStore


def test_event_store_appends_jsonl(tmp_path: Path) -> None:
    store = RepairEventStore(tmp_path / "repair-events.jsonl")
    from coru.repair.events import RepairEvent

    store.append(
        RepairEvent(
            event_type="repair.session.started",
            aggregate_id="cursor/cursor-main",
            payload={"session_id": "s1", "ide": "cursor", "instance": "cursor-main"},
        )
    )
    events = store.read_all()
    assert len(events) == 1
    assert events[0].event_type == "repair.session.started"


def test_drive_diagnostics_detect_submit_unverified() -> None:
    drive = {
        "ok": False,
        "verification": "submit_unverified",
        "winning_paste": "workbench.action.terminal.paste",
        "winning_focus_open": "workbench.panel.chat+composer.focusComposer",
        "message": "paste ok submit failed",
    }
    problems = collect_problems_from_drive_result(drive, ide="cursor")
    codes = {p.code for p in problems}
    assert "submit_unverified" in codes
    assert "terminal_paste_risk" in codes
    assert "chat_focus_toggle_risk" in codes


def test_repair_session_writes_history(tmp_path: Path) -> None:
    service = RepairService(RepairEventStore(tmp_path / "repair-events.jsonl"))

    plan = service.run_session(
        RunRepairSessionCommand(
            ide="cursor",
            instance="cursor-main",
            problems=(
                RepairProblem(
                    code="venv_alignment",
                    severity="warning",
                    message="venv mismatch",
                ),
            ),
            trigger="test",
            session_id="sess-1",
        ),
        repo_root=None,
        run_koru=lambda _args: 0,
        replay=lambda _i, _inst, _args: 0,
        fetch_status=lambda _i, _inst: {},
    )
    assert plan.session_id == "sess-1"
    raw = (tmp_path / "repair-events.jsonl").read_text(encoding="utf-8")
    assert "repair.session.started" in raw
    assert "repair.session.finished" in raw

    history = RepairHistoryQuery(RepairEventStore(tmp_path / "repair-events.jsonl")).format_llm(limit=5)
    assert "venv_alignment" in history
    assert "repair history" in history


def test_run_repair_with_events_persists_to_project_store(tmp_path: Path) -> None:
    run_repair_with_events(
        project_root=tmp_path,
        ide="cursor",
        instance="cursor-main",
        problems=[
            RepairProblem(code="plugin_not_connected", severity="error", message="missing"),
        ],
        trigger="unit-test",
        run_koru=lambda _args: 0,
        replay=lambda _i, _inst, _args: 0,
        fetch_status=lambda _i, _inst: {"plugins": []},
        max_rounds=1,
    )
    store_path = tmp_path / ".planfile" / ".koru" / "repair-events.jsonl"
    assert store_path.is_file()
    lines = store_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2
    first = json.loads(lines[0])
    assert first["schema"] == "coru.repair.event.v1"
