"""Tests for koru.autonomy.shell_drive_finalize."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import koru.queue.ticket as ticket_mod
import koru.tillm_bridge as bridge_mod
from koru.autonomy import post_run_verify as verify_mod
from koru.autonomy.shell_drive_finalize import finalize_shell_drive_ticket


class _PlanfileRecorder:
    def __init__(self, done_rc: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.done_rc = done_rc

    def __call__(self, project: Path, args, runner=None):
        self.calls.append(list(args))
        rc = self.done_rc if args[:2] == ["ticket", "done"] else 0
        return subprocess.CompletedProcess(list(args), rc, stdout="", stderr="")

    def commands(self) -> list[str]:
        return [" ".join(c[:2]) for c in self.calls]


@pytest.fixture()
def planfile(monkeypatch: pytest.MonkeyPatch) -> _PlanfileRecorder:
    rec = _PlanfileRecorder()
    monkeypatch.setattr(ticket_mod, "planfile_command", rec)
    monkeypatch.setattr(bridge_mod, "shell_drive_client_id", lambda ide: "claude-code")
    monkeypatch.delenv("KORU_SHELL_DRIVE_AUTODONE", raising=False)
    return rec


def _hp(_msg: str) -> None:
    pass


def _finalize(tmp_path: Path, **overrides):
    kwargs = dict(
        project=tmp_path,
        autopilot_ide="claude",
        ticket_id="STARTER-1",
        reply={"ok": True, "message": "refactor applied", "client_id": "claude-code"},
        ok=True,
        decision_kind="escalation_prompt",
        _hp=_hp,
    )
    kwargs.update(overrides)
    return finalize_shell_drive_ticket(**kwargs)


def test_skips_non_shell_client(tmp_path, planfile, monkeypatch):
    monkeypatch.setattr(bridge_mod, "shell_drive_client_id", lambda ide: None)
    assert _finalize(tmp_path) == "skipped"
    assert planfile.calls == []


def test_skips_failed_drive_and_wrong_kind(tmp_path, planfile):
    assert _finalize(tmp_path, ok=False) == "skipped"
    assert _finalize(tmp_path, decision_kind="idle_no_ticket") == "skipped"
    assert planfile.calls == []


def test_verified_without_config_only_notes(tmp_path, planfile, monkeypatch):
    monkeypatch.setattr(verify_mod, "load_post_run_verify_config", lambda p: None)
    assert _finalize(tmp_path) == "noted"
    assert planfile.commands() == ["ticket update"]


def test_verified_green_marks_done(tmp_path, planfile, monkeypatch):
    config = verify_mod.PostRunVerifyConfig(enabled=True, commands=("true",))
    monkeypatch.setattr(verify_mod, "load_post_run_verify_config", lambda p: config)
    monkeypatch.setattr(
        verify_mod,
        "verify_completed_tickets",
        lambda project, ids, **kw: [{"ticket_id": i, "ok": True, "action": "verified"} for i in ids],
    )
    assert _finalize(tmp_path) == "done_verified"
    assert planfile.commands() == ["ticket update", "ticket done"]


def test_verified_red_reports_reopen(tmp_path, planfile, monkeypatch):
    config = verify_mod.PostRunVerifyConfig(enabled=True, commands=("false",))
    monkeypatch.setattr(verify_mod, "load_post_run_verify_config", lambda p: config)
    monkeypatch.setattr(
        verify_mod,
        "verify_completed_tickets",
        lambda project, ids, **kw: [{"ticket_id": i, "ok": False, "action": "reopened"} for i in ids],
    )
    assert _finalize(tmp_path) == "verify_failed:reopened"


def test_always_policy_trusts_agent(tmp_path, planfile, monkeypatch):
    monkeypatch.setenv("KORU_SHELL_DRIVE_AUTODONE", "always")
    assert _finalize(tmp_path) == "done"
    assert planfile.commands() == ["ticket update", "ticket done"]


def test_off_policy_only_notes(tmp_path, planfile, monkeypatch):
    monkeypatch.setenv("KORU_SHELL_DRIVE_AUTODONE", "off")
    assert _finalize(tmp_path) == "noted"
    assert planfile.commands() == ["ticket update"]


def test_done_failure_reported(tmp_path, monkeypatch):
    rec = _PlanfileRecorder(done_rc=1)
    monkeypatch.setattr(ticket_mod, "planfile_command", rec)
    monkeypatch.setattr(bridge_mod, "shell_drive_client_id", lambda ide: "claude-code")
    monkeypatch.setenv("KORU_SHELL_DRIVE_AUTODONE", "always")
    assert _finalize(tmp_path) == "done_failed"


def test_bytes_reply_message_survives(tmp_path, planfile, monkeypatch):
    monkeypatch.setenv("KORU_SHELL_DRIVE_AUTODONE", "off")
    result = _finalize(tmp_path, reply={"ok": True, "message": b"\xffraw", "client_id": "codex"})
    assert result == "noted"
    note = planfile.calls[0][-1]
    assert "raw" in note
