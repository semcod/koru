"""Tests for koru.autonomy.verification_engine."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from koru.autonomy.verification_engine import (
    ChatEvidence,
    Evidence,
    GitEvidence,
    Snapshot,
    TestEvidence,
    Verdict,
    assess_verdict,
    collect_chat_evidence,
    collect_git_evidence,
    collect_test_evidence,
    take_snapshot,
    _extract_leading_int,
)


# ---------------------------------------------------------------------------
# _extract_leading_int
# ---------------------------------------------------------------------------


class TestExtractLeadingInt:
    def test_basic(self):
        assert _extract_leading_int(" 3 files changed") == 3

    def test_large_number(self):
        assert _extract_leading_int("142 insertions(+)") == 142

    def test_no_digits(self):
        assert _extract_leading_int("no changes") == 0

    def test_empty(self):
        assert _extract_leading_int("") == 0


# ---------------------------------------------------------------------------
# collect_git_evidence
# ---------------------------------------------------------------------------


class TestCollectGitEvidence:
    def test_parses_stat_output(self, tmp_path: Path):
        fake_output = (
            " src/foo.py | 10 +++++++---\n"
            " src/bar.py |  5 ++---\n"
            " 2 files changed, 10 insertions(+), 5 deletions(-)\n"
        )
        fake_result = subprocess.CompletedProcess([], 0, stdout=fake_output, stderr="")
        with patch("koru.autonomy.verification_engine.subprocess.run", return_value=fake_result):
            ev = collect_git_evidence(tmp_path)
        assert ev.files_changed == 2
        assert ev.insertions == 10
        assert ev.deletions == 5

    def test_no_changes(self, tmp_path: Path):
        fake_result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with patch("koru.autonomy.verification_engine.subprocess.run", return_value=fake_result):
            ev = collect_git_evidence(tmp_path)
        assert ev.files_changed == 0

    def test_git_not_found(self, tmp_path: Path):
        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            ev = collect_git_evidence(tmp_path)
        assert ev.files_changed == 0

    def test_git_error(self, tmp_path: Path):
        fake_result = subprocess.CompletedProcess([], 128, stdout="", stderr="fatal")
        with patch("koru.autonomy.verification_engine.subprocess.run", return_value=fake_result):
            ev = collect_git_evidence(tmp_path)
        assert ev.files_changed == 0


# ---------------------------------------------------------------------------
# collect_test_evidence
# ---------------------------------------------------------------------------


class TestCollectTestEvidence:
    def test_from_wup_health(self):
        class FakeWup:
            status = "ok"
            failing_services = []
            new_events = 3

        ev = collect_test_evidence(FakeWup())
        assert ev.status == "ok"
        assert ev.new_events == 3

    def test_from_none(self):
        ev = collect_test_evidence(None)
        assert ev.status == "unknown"

    def test_failing(self):
        class FakeWup:
            status = "failing"
            failing_services = ["koru-shell"]
            new_events = 1

        ev = collect_test_evidence(FakeWup())
        assert ev.status == "failing"
        assert "koru-shell" in ev.failing_services


# ---------------------------------------------------------------------------
# collect_chat_evidence
# ---------------------------------------------------------------------------


class TestCollectChatEvidence:
    def test_empty_events(self):
        ev = collect_chat_evidence([], 100.0)
        assert ev.events_since_drive == 0

    def test_filters_by_timestamp(self):
        events = [
            {"type": "message.sent", "ts": 90.0},
            {"type": "message.sent", "ts": 110.0},
            {"type": "session.ended", "ts": 120.0},
        ]
        ev = collect_chat_evidence(events, 100.0)
        assert ev.events_since_drive == 2
        assert ev.has_message_sent is True
        assert ev.has_session_ended is True

    def test_no_events_since_drive(self):
        events = [
            {"type": "message.sent", "ts": 50.0},
        ]
        ev = collect_chat_evidence(events, 100.0)
        assert ev.events_since_drive == 0


# ---------------------------------------------------------------------------
# assess_verdict
# ---------------------------------------------------------------------------


class TestAssessVerdict:
    def test_completed_with_git_and_tests(self):
        evidence = Evidence(
            git=GitEvidence(files_changed=3, insertions=50, deletions=10),
            tests=TestEvidence(status="ok"),
            chat=ChatEvidence(has_message_sent=True, has_session_ended=True),
        )
        v = assess_verdict(evidence, ticket_id="T-1")
        assert v.outcome == "completed"
        assert v.confidence >= 0.6
        assert v.ticket_id == "T-1"

    def test_no_change(self):
        evidence = Evidence(
            git=GitEvidence(files_changed=0),
            tests=TestEvidence(status="unknown"),
            chat=ChatEvidence(),
        )
        v = assess_verdict(evidence)
        assert v.outcome == "no_change"
        assert v.confidence < 0.3

    def test_degraded_when_tests_fail(self):
        evidence = Evidence(
            git=GitEvidence(files_changed=2),
            tests=TestEvidence(status="failing", failing_services=("koru-shell",)),
            chat=ChatEvidence(has_message_sent=True),
        )
        v = assess_verdict(evidence)
        assert v.outcome in {"in_progress", "completed", "degraded"}
        assert "failing" in v.reason

    def test_in_progress_partial(self):
        evidence = Evidence(
            git=GitEvidence(files_changed=1),
            tests=TestEvidence(status="unknown"),
            chat=ChatEvidence(),
        )
        v = assess_verdict(evidence)
        assert v.outcome == "in_progress"
        assert 0.3 <= v.confidence < 0.6

    def test_stagnation_note(self):
        evidence = Evidence(
            git=GitEvidence(files_changed=0),
            tests=TestEvidence(status="unknown"),
            chat=ChatEvidence(),
        )
        v = assess_verdict(evidence, drive_count=4)
        assert "stagnant" in v.reason

    def test_pure_chat_activity(self):
        evidence = Evidence(
            git=GitEvidence(files_changed=0),
            tests=TestEvidence(status="ok"),
            chat=ChatEvidence(has_message_sent=True, has_session_ended=True),
        )
        v = assess_verdict(evidence)
        assert v.confidence > 0.0
        assert v.outcome in {"in_progress", "completed"}


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_take_snapshot(self, tmp_path: Path):
        with patch(
            "koru.autonomy.verification_engine.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="abc123\n"),
        ):
            snap = take_snapshot(tmp_path, test_status="ok")
        assert snap.git_head == "abc123"
        assert snap.test_status == "ok"
        assert snap.timestamp > 0

    def test_to_dict(self):
        snap = Snapshot(git_head="abc", git_dirty_count=2, test_status="ok", timestamp=1.0)
        d = snap.to_dict()
        assert d["git_head"] == "abc"


# ---------------------------------------------------------------------------
# Verdict serialization
# ---------------------------------------------------------------------------


class TestVerdictSerialization:
    def test_to_dict(self):
        v = Verdict(
            outcome="completed",
            confidence=0.8,
            reason="test",
            ticket_id="T-1",
        )
        d = v.to_dict()
        assert d["outcome"] == "completed"
        assert d["confidence"] == 0.8
        assert d["ticket_id"] == "T-1"
