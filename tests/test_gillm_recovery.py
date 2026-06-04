"""Tests for gillm recovery bridge in Koru."""

from __future__ import annotations

from koru.decision_engine import build_decision_engine
from koru.ide_adapters.gillm_recovery import enrich_drive_reply_with_recovery, recovery_hints_from_drive_reply


def test_recovery_hints_from_plugin_missing() -> None:
    hints = recovery_hints_from_drive_reply(
        {"ok": False, "message": "no connected autopilot plugin for ide=cursor"}
    )
    assert any("Reload" in hint for hint in hints)


def test_enrich_drive_reply_adds_failure_kind() -> None:
    reply = {"ok": False, "message": "submit could not be verified"}
    enriched = enrich_drive_reply_with_recovery(reply)
    assert enriched["failure_kind"] == "submit_unverified"
    assert enriched["recovery"]


def test_decision_engine_recovery_delegate() -> None:
    engine = build_decision_engine(__import__("pathlib").Path.cwd(), ide="cursor")
    hints = engine.recovery_hints_for_drive_reply(
        {"ok": False, "message": "no connected autopilot plugin for ide=cursor"}
    )
    assert hints
