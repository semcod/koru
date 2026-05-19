"""Tests for `koru gate authorize` (PLF-koru improvement #1).

Verifies that gate authorizations are stored as structured, parseable
notes — not free-text — so downstream audit tooling can reason about
which gates were waived by whom and why.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from koru.gate import (
    GATE_AUTH_TAG,
    VALID_MODES,
    GateAuthorization,
    authorize_gate,
    parse_authorizations,
)


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _fail(stderr: str = "boom") -> SimpleNamespace:
    return SimpleNamespace(returncode=1, stdout="", stderr=stderr)


def test_authorize_gate_records_structured_note(tmp_path):
    """The note must start with KORU-GATE-AUTH and contain valid JSON."""
    captured: dict = {}

    def fake_runner(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = kwargs
        return _ok()

    auth = authorize_gate(
        "PLF-070",
        mode="advisory",
        skipped=["task test", "task quality:gate"],
        reason="agent ran regix:local + pytest subset; full CI deferred",
        project=tmp_path,
        authorized_by="tom",
        runner=fake_runner,
    )

    assert isinstance(auth, GateAuthorization)
    assert auth.mode == "advisory"
    assert auth.skipped == ("task test", "task quality:gate")
    assert auth.authorized_by == "tom"
    assert auth.ticket == "PLF-070"
    # Authorization timestamp is ISO-8601 UTC with Z suffix
    assert auth.authorized_at.endswith("Z")

    # The CLI command sent to planfile must include --note with our payload
    cmd = captured["cmd"]
    assert "ticket" in cmd and "update" in cmd
    note_index = cmd.index("--note")
    note = cmd[note_index + 1]
    assert note.startswith(f"{GATE_AUTH_TAG} ")
    payload = json.loads(note[len(GATE_AUTH_TAG) + 1 :])
    assert payload["kind"] == "gate_authorization"
    assert payload["mode"] == "advisory"
    assert payload["skipped"] == ["task test", "task quality:gate"]


def test_authorize_gate_rejects_unknown_mode(tmp_path):
    with pytest.raises(ValueError, match="unknown gate mode"):
        authorize_gate(
            "PLF-001",
            mode="yolo",
            skipped=[],
            reason="anything",
            project=tmp_path,
            runner=lambda *_a, **_kw: _ok(),
        )


def test_authorize_gate_requires_reason(tmp_path):
    with pytest.raises(ValueError, match="reason"):
        authorize_gate(
            "PLF-001",
            mode="advisory",
            skipped=[],
            reason="   ",  # blank → must reject
            project=tmp_path,
            runner=lambda *_a, **_kw: _ok(),
        )


def test_authorize_gate_propagates_planfile_failure(tmp_path):
    with pytest.raises(RuntimeError, match="planfile ticket update failed"):
        authorize_gate(
            "PLF-001",
            mode="advisory",
            skipped=[],
            reason="anything",
            project=tmp_path,
            runner=lambda *_a, **_kw: _fail("ticket not found"),
        )


def test_parse_authorizations_round_trip():
    """A serialised authorization should parse back to an equal record."""
    original = GateAuthorization(
        mode="advisory",
        skipped=("task test",),
        reason="why",
        authorized_by="tom",
        authorized_at="2026-05-11T10:00:00Z",
        ticket="PLF-070",
    )
    notes = [
        "unrelated note from earlier",
        original.to_note(),
        "another unrelated note",
    ]
    parsed = parse_authorizations(notes)
    assert len(parsed) == 1
    assert parsed[0] == original


def test_parse_authorizations_ignores_malformed_or_unrelated_notes():
    notes = [
        f"{GATE_AUTH_TAG} not-json-at-all",
        f'{GATE_AUTH_TAG} {{"kind": "something_else"}}',  # wrong kind
        f'{GATE_AUTH_TAG} {{"kind": "gate_authorization", "mode": "bogus"}}',  # invalid mode
        "[normal note]",
        None,  # non-string entries must not crash
        42,
    ]
    parsed = parse_authorizations(notes)  # type: ignore[arg-type]
    assert parsed == []


def test_parse_authorizations_returns_records_in_insertion_order():
    a = GateAuthorization(
        mode="advisory",
        skipped=(),
        reason="first",
        authorized_by="alice",
        authorized_at="2026-05-11T10:00:00Z",
        ticket="PLF-070",
    )
    b = GateAuthorization(
        mode="auto",
        skipped=(),
        reason="second",
        authorized_by="bob",
        authorized_at="2026-05-12T10:00:00Z",
        ticket="PLF-070",
    )
    parsed = parse_authorizations([a.to_note(), b.to_note()])
    assert [auth.reason for auth in parsed] == ["first", "second"]
    # Most recent waiver = last element
    assert parsed[-1].mode == "auto"


def test_valid_modes_constant_matches_documented_set():
    """If the set of valid modes changes, the parser + CLI must be
    updated together. This test pins the contract."""
    assert set(VALID_MODES) == {"advisory", "auto", "mandatory_human"}
