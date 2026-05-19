"""Tests for `koru queue clean` — fixture sweeper.

The cleaner has three responsibilities that all need pinning down:

1. **Selection** — only fixture-shaped tickets are picked up; real
   work is left alone (`find_candidates`).
2. **Safety** — by default ``in_progress`` / ``waiting_input`` tickets
   are surfaced as ``skipped_active`` instead of swept (no surprise
   interruptions of human work).
3. **Audit** — every closure carries a structured KORU-QUEUE-CLEAN
   note so future investigations can answer "who killed PLF-XXX?".
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from koru.queue_clean import (
    QUEUE_CLEAN_TAG,
    CleanupCandidate,
    CleanupReport,
    clean_queue,
    find_candidates,
)


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _fail(stderr: str = "boom", code: int = 1) -> SimpleNamespace:
    return SimpleNamespace(returncode=code, stdout="", stderr=stderr)


# ---------------------------------------------------------------------------
# find_candidates — pure-function selection logic
# ---------------------------------------------------------------------------


def test_label_match_picks_only_fixture_labelled_tickets():
    tickets = [
        {"id": "PLF-1", "name": "Real work", "status": "open", "labels": ["bug"]},
        {
            "id": "PLF-2",
            "name": "Test fixture",
            "status": "open",
            "labels": ["test-only", "dryrun"],
        },
        {"id": "PLF-3", "name": "Synthetic alert", "status": "open", "labels": ["synthetic"]},
        {"id": "PLF-4", "name": "Already done", "status": "done", "labels": ["test-only"]},
    ]
    candidates, skipped = find_candidates(tickets)
    ids = sorted(c.ticket_id for c in candidates)
    assert ids == ["PLF-2", "PLF-3"]
    assert skipped == []
    # Each candidate carries the rule that selected it
    for c in candidates:
        assert any(r.startswith("fixture-label") for r in c.matched_rules)


def test_name_heuristic_only_runs_when_explicit():
    tickets = [{"id": "PLF-9", "name": "Test foo", "status": "open", "labels": []}]
    # Default — no opt-in: name doesn't match any rule, ticket ignored.
    candidates, _ = find_candidates(tickets)
    assert candidates == []
    # Opt-in flag: the same ticket is now picked up.
    candidates, _ = find_candidates(tickets, include_names=True)
    assert [c.ticket_id for c in candidates] == ["PLF-9"]
    assert "fixture-name" in candidates[0].matched_rules


def test_name_heuristic_does_not_match_real_tickets_with_test_word():
    """Real bug tickets often contain 'test' as a word — must NOT match."""
    tickets = [
        {"id": "PLF-10", "name": "Fix flaky integration test", "status": "open", "labels": ["bug"]},
        {"id": "PLF-11", "name": "Improve test coverage", "status": "open", "labels": ["chore"]},
    ]
    candidates, _ = find_candidates(tickets, include_names=True)
    assert candidates == []


def test_active_tickets_skipped_by_default_but_surfaced():
    """in_progress + waiting_input tickets must be surfaced explicitly."""
    tickets = [
        {
            "id": "PLF-1",
            "name": "Test fixture in flight",
            "status": "in_progress",
            "labels": ["test-only"],
        },
        {
            "id": "PLF-2",
            "name": "Test fixture pending input",
            "status": "waiting_input",
            "labels": ["dryrun"],
        },
        {"id": "PLF-3", "name": "Test fixture parked", "status": "open", "labels": ["test-only"]},
    ]
    candidates, skipped = find_candidates(tickets)
    assert [c.ticket_id for c in candidates] == ["PLF-3"]
    assert sorted(skipped) == ["PLF-1", "PLF-2"]


def test_include_active_promotes_skipped_back_to_candidates():
    tickets = [
        {
            "id": "PLF-1",
            "name": "Test fixture in flight",
            "status": "in_progress",
            "labels": ["test-only"],
        },
        {"id": "PLF-2", "name": "Test fixture parked", "status": "open", "labels": ["test-only"]},
    ]
    candidates, skipped = find_candidates(tickets, include_active=True)
    assert sorted(c.ticket_id for c in candidates) == ["PLF-1", "PLF-2"]
    assert skipped == []


def test_max_age_modifies_but_never_alone():
    """max-age is a *filter on top of* fixture match — never the sole reason."""
    now = datetime(2026, 5, 11, tzinfo=UTC)
    old_unrelated = (now - timedelta(days=30)).isoformat()
    young_fixture = (now - timedelta(days=1)).isoformat()
    old_fixture = (now - timedelta(days=14)).isoformat()
    tickets = [
        # old, but no fixture rule fires → must NOT be a candidate.
        {
            "id": "PLF-1",
            "name": "Old real bug",
            "status": "open",
            "labels": ["bug"],
            "created_at": old_unrelated,
        },
        # fixture but young → match if max_age=None, miss if max_age=10.
        {
            "id": "PLF-2",
            "name": "Young fixture",
            "status": "open",
            "labels": ["test-only"],
            "created_at": young_fixture,
        },
        # fixture and old → matches both ways.
        {
            "id": "PLF-3",
            "name": "Old fixture",
            "status": "open",
            "labels": ["test-only"],
            "created_at": old_fixture,
        },
    ]
    no_age, _ = find_candidates(tickets, now=now)
    assert sorted(c.ticket_id for c in no_age) == ["PLF-2", "PLF-3"]

    with_age, _ = find_candidates(tickets, max_age_days=10, now=now)
    assert sorted(c.ticket_id for c in with_age) == ["PLF-2", "PLF-3"]
    # Both still match because fixture-label always fires; max-age just adds
    # an extra rule on PLF-3.
    rules_3 = next(c for c in with_age if c.ticket_id == "PLF-3").matched_rules
    rules_2 = next(c for c in with_age if c.ticket_id == "PLF-2").matched_rules
    assert any(r.startswith("age>=") for r in rules_3)
    assert all(not r.startswith("age>=") for r in rules_2)


def test_age_calculation_handles_z_suffix_and_naive_dates():
    now = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    tickets = [
        {
            "id": "PLF-Z",
            "name": "Test",
            "status": "open",
            "labels": ["test-only"],
            "created_at": "2026-05-01T12:00:00Z",
        },
        {
            "id": "PLF-N",
            "name": "Test",
            "status": "open",
            "labels": ["test-only"],
            "created_at": "2026-05-09T12:00:00",
        },  # naive
        {"id": "PLF-X", "name": "Test", "status": "open", "labels": ["test-only"]},  # no created_at
    ]
    candidates, _ = find_candidates(tickets, now=now)
    by_id = {c.ticket_id: c.age_days for c in candidates}
    assert by_id["PLF-Z"] == pytest.approx(10.0, abs=0.01)
    assert by_id["PLF-N"] == pytest.approx(2.0, abs=0.01)
    assert by_id["PLF-X"] is None


# ---------------------------------------------------------------------------
# clean_queue — end-to-end with stubbed runner
# ---------------------------------------------------------------------------


def _list_response(tickets: list[dict]) -> SimpleNamespace:
    return _ok(json.dumps(tickets))


def test_clean_queue_dry_run_lists_but_does_not_close(tmp_path):
    """Dry run must enumerate candidates but never call ticket complete."""
    tickets = [
        {"id": "PLF-1", "name": "Real bug", "status": "open", "labels": ["bug"]},
        {"id": "PLF-2", "name": "Test foo", "status": "open", "labels": ["test-only"]},
    ]
    calls: list[list[str]] = []

    def runner(cmd, **kwargs):
        calls.append(list(cmd))
        if "list" in cmd:
            return _list_response(tickets)
        # Any other command (e.g. complete) must not happen in dry-run.
        raise AssertionError(f"unexpected runner call in dry-run: {cmd}")

    report = clean_queue(tmp_path, runner=runner)
    assert isinstance(report, CleanupReport)
    assert report.dry_run is True
    assert [c.ticket_id for c in report.candidates] == ["PLF-2"]
    assert report.applied == []
    # Exactly one call: the list query.
    assert len(calls) == 1
    assert "list" in calls[0]


def test_clean_queue_apply_closes_each_candidate_with_audit_note(tmp_path):
    tickets = [
        {"id": "PLF-1", "name": "Test foo", "status": "open", "labels": ["test-only"]},
        {"id": "PLF-2", "name": "Test bar", "status": "ready", "labels": ["synthetic"]},
    ]
    captured_completes: list[dict] = []

    def runner(cmd, **kwargs):
        if "list" in cmd:
            return _list_response(tickets)
        if "complete" in cmd:
            tid = cmd[cmd.index("complete") + 1]
            note = cmd[cmd.index("--note") + 1]
            captured_completes.append({"ticket_id": tid, "note": note})
            return _ok()
        raise AssertionError(f"unexpected command: {cmd}")

    report = clean_queue(tmp_path, apply=True, runner=runner)
    assert sorted(report.applied) == ["PLF-1", "PLF-2"]
    assert report.failed == []
    assert len(captured_completes) == 2
    for entry in captured_completes:
        assert entry["note"].startswith(QUEUE_CLEAN_TAG + " ")
        payload = json.loads(entry["note"][len(QUEUE_CLEAN_TAG) + 1 :])
        assert payload["kind"] == "queue_cleanup"
        assert payload["rules"]
        assert payload["reason"]
        assert payload["cleaned_at"].endswith("Z")


def test_clean_queue_records_failures_per_ticket(tmp_path):
    tickets = [
        {"id": "PLF-A", "name": "Test", "status": "open", "labels": ["test-only"]},
        {"id": "PLF-B", "name": "Test", "status": "open", "labels": ["test-only"]},
    ]

    def runner(cmd, **kwargs):
        if "list" in cmd:
            return _list_response(tickets)
        if "complete" in cmd:
            tid = cmd[cmd.index("complete") + 1]
            if tid == "PLF-B":
                return _fail("ticket locked")
            return _ok()
        raise AssertionError(f"unexpected: {cmd}")

    report = clean_queue(tmp_path, apply=True, runner=runner)
    assert report.applied == ["PLF-A"]
    assert report.failed == [("PLF-B", "ticket locked")]


def test_clean_queue_propagates_list_failure_as_runtime_error(tmp_path):
    def runner(cmd, **kwargs):
        return _fail("backend offline", code=2)

    with pytest.raises(RuntimeError, match="planfile ticket list failed"):
        clean_queue(tmp_path, runner=runner)


def test_clean_queue_handles_empty_list_gracefully(tmp_path):
    def runner(cmd, **kwargs):
        if "list" in cmd:
            return _ok("[]")
        raise AssertionError("complete should not be called on empty list")

    report = clean_queue(tmp_path, apply=True, runner=runner)
    assert report.candidates == []
    assert report.applied == []
    assert report.failed == []


def test_cleanup_candidate_explanation_is_human_readable():
    candidate = CleanupCandidate(
        ticket_id="PLF-9",
        name="Test foo",
        status="open",
        labels=("test-only",),
        age_days=2.5,
        matched_rules=("fixture-label(test-only)", "fixture-name"),
    )
    text = candidate.explanation()
    assert "PLF-9" in text
    assert "open" in text
    assert "2.5d" in text
    assert "fixture-label(test-only)" in text


def test_report_to_dict_is_json_serialisable():
    """The CLI's --format json path round-trips report.to_dict()."""
    report = CleanupReport(
        candidates=[
            CleanupCandidate(
                ticket_id="PLF-1",
                name="Test",
                status="open",
                labels=("test-only",),
                age_days=1.0,
                matched_rules=("fixture-label(test-only)",),
            ),
        ],
        applied=["PLF-1"],
        failed=[("PLF-2", "boom")],
        skipped_active=["PLF-3"],
        dry_run=False,
    )
    serialised = json.dumps(report.to_dict(), sort_keys=True)
    parsed = json.loads(serialised)
    assert parsed["dry_run"] is False
    assert parsed["candidate_count"] == 1
    assert parsed["applied_count"] == 1
    assert parsed["failed_count"] == 1
    assert parsed["skipped_active_count"] == 1
    assert parsed["failed"] == [{"ticket_id": "PLF-2", "error": "boom"}]
