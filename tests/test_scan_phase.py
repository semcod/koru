from __future__ import annotations

from pathlib import Path

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
