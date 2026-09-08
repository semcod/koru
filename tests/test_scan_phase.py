from __future__ import annotations

from pathlib import Path

import pytest

from koru.autonomy import code2llm_discovery as code2llm_discovery_mod
from koru.autonomy import ide_work as ide_work_mod
from koru.autonomy.phases import scan_phase
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.scan import ScanResult, Suggestion


def _create_failed_result() -> ScanResult:
    return ScanResult(
        suggestions=[
            Suggestion(
                signal="code2llm_cc",
                title="Reduce CC",
                description="desc",
            )
        ],
        applied=[],
        skipped=["Reduce CC"],
        skipped_create_failed=["Reduce CC"],
        skipped_create_failed_details=["Reduce CC: lock busy"],
    )


def _duplicate_only_result() -> ScanResult:
    return ScanResult(
        suggestions=[
            Suggestion(
                signal="code2llm_cc",
                title="Reduce CC",
                description="desc",
            )
        ],
        applied=[],
        skipped=["Reduce CC"],
        skipped_as_duplicate=["Reduce CC"],
    )


def test_handle_scan_phase_skips_repeated_create_failed_during_cooldown(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logs: list[str] = []
    emits: list[tuple[str, dict]] = []
    state = AutoloopState(
        last_scan_create_failed_fingerprint="1:deadbeef",
        last_scan_create_failed_ts=100.0,
    )

    monkeypatch.setattr(scan_phase.time, "time", lambda: 120.0)
    monkeypatch.setattr(scan_phase, "is_topology_enabled", lambda *_a, **_k: True)

    result = scan_phase.handle_scan_phase(
        tmp_path,
        state,
        12,
        True,
        False,
        False,
        1,
        False,
        logs.append,
        lambda kind, payload, **_kwargs: emits.append((kind, payload)),
    )

    assert result is None
    assert any("repeated create_failed" in line for line in logs)
    assert emits == [
        (
            "ScanSkipped",
            {
                "cycle": 12,
                "reason": "create_failed_cooldown",
                "cooldown_remaining_seconds": 100.0,
            },
        )
    ]


def test_handle_scan_phase_skips_repeated_duplicate_only_scan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logs: list[str] = []
    emits: list[tuple[str, dict]] = []
    state = AutoloopState(
        last_scan_duplicate_fingerprint="1:deadbeef",
        last_scan_duplicate_ts=100.0,
    )

    monkeypatch.setattr(scan_phase.time, "time", lambda: 120.0)
    monkeypatch.setattr(scan_phase, "is_topology_enabled", lambda *_a, **_k: True)

    result = scan_phase.handle_scan_phase(
        tmp_path,
        state,
        13,
        True,
        False,
        False,
        1,
        False,
        logs.append,
        lambda kind, payload, **_kwargs: emits.append((kind, payload)),
    )

    assert result is None
    assert any("duplicate-only results" in line for line in logs)
    assert emits == [
        (
            "ScanSkipped",
            {
                "cycle": 13,
                "reason": "duplicate_only_cooldown",
                "cooldown_remaining_seconds": 280.0,
            },
        )
    ]


def test_handle_scan_after_idle_remembers_create_failed_and_skips_next_attempt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logs: list[str] = []
    emits: list[tuple[str, dict]] = []
    state = AutoloopState()
    telemetry: dict[str, object] = {}
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=[],
        last_status="idle",
        last_message="",
        last_ticket_id=None,
    )
    first_result = _create_failed_result()
    calls = {"count": 0}
    clock = {"now": 100.0}

    def fake_time() -> float:
        return float(clock["now"])

    def fake_run_scan(**_kwargs) -> ScanResult:
        calls["count"] += 1
        return first_result

    monkeypatch.setattr(scan_phase.time, "time", fake_time)
    monkeypatch.setattr(scan_phase, "is_topology_enabled", lambda *_a, **_k: True)
    monkeypatch.setattr(scan_phase, "run_scan", fake_run_scan)

    first = scan_phase.handle_scan_after_idle(
        tmp_path,
        state,
        1,
        queue_result,
        True,
        False,
        0.0,
        False,
        telemetry,
        logs.append,
        lambda kind, payload, **_kwargs: emits.append((kind, payload)),
    )

    assert first == first_result
    assert calls["count"] == 1
    assert state.last_scan_create_failed_fingerprint
    assert telemetry["scan_after_idle_run"] is True

    clock["now"] = 130.0
    second = scan_phase.handle_scan_after_idle(
        tmp_path,
        state,
        2,
        queue_result,
        True,
        False,
        0.0,
        False,
        telemetry,
        logs.append,
        lambda kind, payload, **_kwargs: emits.append((kind, payload)),
    )

    assert second is None
    assert calls["count"] == 1
    assert telemetry["scan_after_idle_skipped_create_failed_cooldown"] is True
    assert any("repeated create_failed" in line for line in logs)


def test_handle_scan_after_idle_remembers_duplicates_and_skips_next_attempt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logs: list[str] = []
    emits: list[tuple[str, dict]] = []
    state = AutoloopState()
    telemetry: dict[str, object] = {}
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=[],
        last_status="idle",
        last_message="",
        last_ticket_id=None,
    )
    calls = {"count": 0}
    clock = {"now": 100.0}

    def fake_time() -> float:
        return float(clock["now"])

    def fake_run_scan(**_kwargs) -> ScanResult:
        calls["count"] += 1
        return _duplicate_only_result()

    monkeypatch.setattr(scan_phase.time, "time", fake_time)
    monkeypatch.setattr(scan_phase, "is_topology_enabled", lambda *_a, **_k: True)
    monkeypatch.setattr(scan_phase, "run_scan", fake_run_scan)

    first = scan_phase.handle_scan_after_idle(
        tmp_path,
        state,
        1,
        queue_result,
        True,
        False,
        0.0,
        False,
        telemetry,
        logs.append,
        lambda kind, payload, **_kwargs: emits.append((kind, payload)),
    )

    assert first is not None
    assert calls["count"] == 1
    assert state.last_scan_duplicate_fingerprint

    clock["now"] = 130.0
    second = scan_phase.handle_scan_after_idle(
        tmp_path,
        state,
        2,
        queue_result,
        True,
        False,
        0.0,
        False,
        telemetry,
        logs.append,
        lambda kind, payload, **_kwargs: emits.append((kind, payload)),
    )

    assert second is None
    assert calls["count"] == 1
    assert telemetry["scan_after_idle_skipped_duplicate_cooldown"] is True
    assert any("duplicate-only results" in line for line in logs)


def test_run_code2llm_discovery_after_idle_ensures_standardized_follow_up_ticket(
    tmp_path: Path,
    monkeypatch,
) -> None:
    logs: list[str] = []
    emits: list[tuple[str, dict]] = []
    outcome = code2llm_discovery_mod.DiscoveryOutcome(
        ran=True,
        code2llm_returncode=0,
        applied_titles=[],
        skipped_titles=[],
    )

    monkeypatch.setattr(
        code2llm_discovery_mod,
        "run_code2llm_discovery",
        lambda _project, **_: outcome,
    )
    monkeypatch.setattr(
        code2llm_discovery_mod,
        "format_discovery_summary",
        lambda _outcome: "code2llm discovery: applied=0 skipped=0",
    )
    monkeypatch.setattr(
        ide_work_mod,
        "ensure_project_discovery_ticket",
        lambda _project, *, auto_run_code2llm: {
            "id": "PLF-777",
            "name": "Project discovery",
        },
    )

    payload = scan_phase._run_code2llm_discovery_after_idle(
        tmp_path,
        logs.append,
        lambda kind, payload, **_kwargs: emits.append((kind, payload)),
    )

    assert payload is not None
    assert payload["follow_up_workflow"] == "standardized_project_discovery"
    assert payload["follow_up_ticket_id"] == "PLF-777"
    assert any("standardized follow-up ticket PLF-777" in line for line in logs)
    assert emits and emits[-1][0] == "Code2llmDiscoveryCompleted"
    assert emits[-1][1]["follow_up_ticket_id"] == "PLF-777"


def test_run_code2llm_discovery_after_idle_skips_follow_up_when_tickets_applied(
    tmp_path: Path,
    monkeypatch,
) -> None:
    outcome = code2llm_discovery_mod.DiscoveryOutcome(
        ran=True,
        code2llm_returncode=0,
        applied_titles=["Split god module"],
        skipped_titles=[],
    )
    called = {"ensure": 0}

    monkeypatch.setattr(
        code2llm_discovery_mod,
        "run_code2llm_discovery",
        lambda _project, **_: outcome,
    )
    monkeypatch.setattr(
        code2llm_discovery_mod,
        "format_discovery_summary",
        lambda _outcome: "code2llm discovery: applied=1 skipped=0",
    )

    def _unexpected_ensure(_project, *, auto_run_code2llm):
        called["ensure"] += 1
        return {"id": "PLF-778"}

    monkeypatch.setattr(
        ide_work_mod,
        "ensure_project_discovery_ticket",
        _unexpected_ensure,
    )

    payload = scan_phase._run_code2llm_discovery_after_idle(
        tmp_path,
        lambda _line: None,
        lambda *_args, **_kwargs: None,
    )

    assert payload is not None
    assert "follow_up_ticket_id" not in payload
    assert called["ensure"] == 0


@pytest.mark.parametrize("cooldown", [False, True])
@pytest.mark.parametrize("enabled,discovery,todo,expected", [
    (False, None, None, ["nxdo"]),
    (True, {"applied": ["C-1"]}, None, ["code2llm"]),
    (True, None, {"applied": ["T-1"]}, ["code2llm", "todo2code", "autonomy"]),
    (True, {}, {"useful_plans_count": 1}, ["code2llm", "todo2code", "autonomy", "nxdo"]),
    (True, None, None, ["code2llm", "todo2code", "nxdo"]),
])
def test_idle_discovery_fallback_contract(monkeypatch, tmp_path, cooldown, enabled, discovery, todo, expected):
    calls = []
    records = []
    state = AutoloopState()
    telemetry = {}
    scan = ScanResult(suggestions=[], applied=[], skipped=[])
    monkeypatch.setattr(scan_phase, "_scan_paths_for_project", lambda p: ("src",))
    monkeypatch.setattr(scan_phase, "run_scan", lambda **k: scan)
    monkeypatch.setattr(scan_phase, "_should_skip_repeated_duplicate_scan", lambda s: (True, 10))

    def code2llm(project, hp, emit, *, scope_paths):
        assert project == tmp_path and scope_paths == ("src",)
        calls.append("code2llm")
        return discovery

    def todo2code(*args):
        calls.append("todo2code")
        return todo

    def autonomy(*args):
        calls.append("autonomy")
        return {"ran": True}

    def nxdo(*args):
        calls.append("nxdo")
        return {"ran": True}

    def record(s, t, payload):
        assert s is state and t is telemetry
        records.append(payload)

    monkeypatch.setattr(scan_phase, "_run_code2llm_discovery_after_idle", code2llm)
    monkeypatch.setattr(scan_phase, "_run_todo2code_discovery_after_idle", todo2code)
    monkeypatch.setattr(scan_phase, "_run_code_change_autonomy_after_idle", autonomy)
    monkeypatch.setattr(scan_phase, "_run_nxdo_discovery_after_idle", nxdo)
    for name in ("code2llm_discovery", "todo2code_discovery", "code_change_autonomy", "nxdo_discovery"):
        monkeypatch.setattr(scan_phase, f"_record_{name}_telemetry", record)
    if cooldown:
        assert scan_phase._skip_scan_after_idle_for_duplicate_cooldown(
            tmp_path, state, 1, enabled, telemetry, lambda *a: None, lambda *a, **k: None,
        ) is True
    else:
        assert scan_phase._run_scan_after_idle(
            tmp_path, state, 1, enabled, 100.0, telemetry, lambda *a: None, lambda *a, **k: None,
        ) is scan
    assert calls == expected
    payloads = {"code2llm": discovery, "todo2code": todo, "autonomy": {"ran": True}, "nxdo": {"ran": True}}
    assert records == [payloads[name] for name in expected]
