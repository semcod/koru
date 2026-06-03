"""Tests for IDE operator guidance helpers."""

from __future__ import annotations

from koru.autonomy import ide_operator_guidance as guidance


def test_classify_drive_failure_paste_probe() -> None:
    steps = guidance.classify_drive_failure_guidance(
        {
            "paste_failure_reason": "chat input probe inconclusive; refusing terminal-risk paste fallback",
            "opened": True,
            "ok": False,
        },
        ide="vscodium",
    )
    assert steps is not None
    assert any("cursor" in line.lower() for line in steps)


def test_classify_drive_failure_submit() -> None:
    steps = guidance.classify_drive_failure_guidance(
        {"verification": "submit_unverified", "delivered": True, "submitted": False},
        ide="cursor",
    )
    assert steps is not None
    assert any("enter" in line.lower() or "send" in line.lower() for line in steps)


def test_lane_mismatch_integrated_steps() -> None:
    steps = guidance.lane_mismatch_operator_steps(
        terminal_ide="cursor",
        target_ide="vscodium",
        terminal_kind="integrated",
        lane="vscodium",
    )
    assert any("cursor" in line.lower() for line in steps)
    assert any("vscodium" in line.lower() for line in steps)


def test_terminal_kind_label() -> None:
    assert "integrated" in guidance.terminal_kind_label("integrated")
    assert "external" in guidance.terminal_kind_label("ide_adjacent")
