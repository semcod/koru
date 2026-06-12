from __future__ import annotations

from koru.autonomy.drive_strategies import (
    DriveStrategy,
    DriveStrategyContext,
    execute_drive_strategies,
)


def _context() -> DriveStrategyContext:
    return DriveStrategyContext(
        client=None,
        prompt="hello",
        submit=True,
        autopilot_ide="jetbrains",
        require_plugin=False,
    )


def test_execute_drive_strategies_returns_first_success() -> None:
    calls: list[str] = []

    result = execute_drive_strategies(
        [
            DriveStrategy("first", lambda ctx: calls.append("first") or {"ok": False}),
            DriveStrategy("second", lambda ctx: calls.append("second") or {"ok": True}),
            DriveStrategy("third", lambda ctx: calls.append("third") or {"ok": True}),
        ],
        _context(),
    )

    assert result == ({"ok": True}, True)
    assert calls == ["first", "second"]


def test_execute_drive_strategies_returns_terminal_failure() -> None:
    result = execute_drive_strategies(
        [
            DriveStrategy("first", lambda ctx: {"ok": False}, return_on_failure=True),
            DriveStrategy("second", lambda ctx: {"ok": True}),
        ],
        _context(),
    )

    assert result == ({"ok": False}, False)


def test_execute_drive_strategies_keeps_last_configured_failure() -> None:
    result = execute_drive_strategies(
        [
            DriveStrategy("ignored", lambda ctx: {"ok": False}),
            DriveStrategy("kept", lambda ctx: {"ok": False, "backend": "gillm"}, keep_failure=True),
        ],
        _context(),
    )

    assert result == ({"ok": False, "backend": "gillm"}, False)
