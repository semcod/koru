"""Tests for IDE window reload automation."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from koru.autonomy import env as autonomy_env
from koru.ide_adapters import ide_reload


def test_keyboard_fallback_when_plugin_missing_default_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default policy is plugin-only: an idle Wayland session must not opt-in.

    Blind OS-injector shots into the active monitor caused cycle-516 style
    regressions where Koru clobbered the wrong window; users must opt in
    explicitly via ``KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN=1``.
    """
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.delenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)
    assert autonomy_env.keyboard_fallback_when_plugin_missing("cursor") is False
    assert autonomy_env.plugin_required_for_ide("cursor") is True
    assert autonomy_env.plugin_required_for_ide("cursor-main") is True


def test_keyboard_fallback_when_plugin_missing_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", "1")
    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)
    assert autonomy_env.keyboard_fallback_when_plugin_missing("cursor") is True
    assert autonomy_env.plugin_required_for_ide("cursor") is False


def test_keyboard_fallback_when_plugin_missing_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", "0")
    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)
    assert autonomy_env.keyboard_fallback_when_plugin_missing("cursor") is False
    assert autonomy_env.plugin_required_for_ide("cursor") is True


def test_reload_via_command_palette_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """OS strategy gets the focus + each key sequence; reload reports success."""
    from gillm.focus.strategy import FocusOutcome

    strategy = _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=True, method="xdotool"),
        focus_methods=("xdotool",),
    )
    monkeypatch.setattr(ide_reload.time, "sleep", lambda *_a: None)
    outcome = ide_reload.reload_via_command_palette("cursor")
    assert outcome.ok is True
    assert outcome.method == "command_palette"
    assert strategy.focus_window.called
    assert strategy.inject_keys.call_count == 3


def test_try_reload_skipped_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_AUTO_RELOAD_IDE", "0")
    outcome = ide_reload.try_reload_vscode_family_ide("cursor", project=Path("/tmp/p"))
    assert outcome.attempted is False


def test_reuse_window_reload_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", raising=False)
    assert ide_reload.reuse_window_reload_enabled() is False


def test_reuse_window_reload_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", "1")
    assert ide_reload.reuse_window_reload_enabled() is True


def test_new_window_reload_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_NEW_WINDOW_RELOAD", raising=False)
    assert ide_reload.new_window_reload_enabled() is False
    monkeypatch.setenv("KORU_AUTOPILOT_NEW_WINDOW_RELOAD", "1")
    assert ide_reload.new_window_reload_enabled() is True


def test_editor_cli_env_drops_extension_host_shims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VSCODE_PID", "123")
    monkeypatch.setenv("VSCODE_IPC_HOOK", "/run/user/1000/vscode.sock")
    monkeypatch.setenv("VSCODE_CWD", "/home/tom")
    monkeypatch.setenv("ELECTRON_RUN_AS_NODE", "1")
    monkeypatch.setenv("ELECTRON_NO_ATTACH_CONSOLE", "1")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")

    env = ide_reload._editor_cli_env()

    assert "VSCODE_PID" not in env
    assert "VSCODE_IPC_HOOK" not in env
    assert "VSCODE_CWD" not in env
    assert "ELECTRON_RUN_AS_NODE" not in env
    assert "ELECTRON_NO_ATTACH_CONSOLE" not in env
    assert env["WAYLAND_DISPLAY"] == "wayland-0"


def test_try_reload_does_not_call_reuse_window_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Reload must NOT silently switch the user's open workspace.

    `cursor -r <project>` replaces whatever the IDE window currently has open
    with the koru project. When koru auto runs against project A while the
    user is editing project B in Cursor, that destroys the user's session.
    Verify the destructive fallback stays disabled unless explicitly opted in.
    """
    monkeypatch.delenv("KORU_AUTOPILOT_AUTO_RELOAD_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", raising=False)
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: False)
    from gillm.focus.strategy import FocusOutcome

    _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=False),
    )
    monkeypatch.setattr(
        ide_reload,
        "config_home_for_ide",
        lambda _ide: Path("/tmp/cursor-config"),
    )

    reopen_calls: list[Path] = []

    def fake_reopen(ide: str, project: Path) -> ide_reload.IdeReloadOutcome:
        reopen_calls.append(project)
        return ide_reload.IdeReloadOutcome(
            attempted=True, ok=True, method="reuse_window"
        )

    monkeypatch.setattr(ide_reload, "reload_via_reopen_workspace", fake_reopen)
    outcome = ide_reload.try_reload_vscode_family_ide("cursor", project=tmp_path)
    assert reopen_calls == [], (
        "reuse_window fallback must be gated behind "
        "KORU_AUTOPILOT_REUSE_WINDOW_RELOAD=1 to protect the user's open workspace"
    )
    assert outcome.ok is False
    assert "command-palette reload disabled by default" in (outcome.detail or "")
    assert "KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD=1" in (outcome.detail or "")


def test_try_reload_calls_reuse_window_when_opted_in(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_AUTO_RELOAD_IDE", raising=False)
    monkeypatch.setenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", "1")
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: False)
    from gillm.focus.strategy import FocusOutcome

    _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=False),
    )
    monkeypatch.setattr(
        ide_reload,
        "config_home_for_ide",
        lambda _ide: Path("/tmp/cursor-config"),
    )

    reopen_calls: list[Path] = []

    def fake_reopen(ide: str, project: Path) -> ide_reload.IdeReloadOutcome:
        reopen_calls.append(project)
        return ide_reload.IdeReloadOutcome(
            attempted=True, ok=True, method="reuse_window"
        )

    monkeypatch.setattr(ide_reload, "reload_via_reopen_workspace", fake_reopen)
    outcome = ide_reload.try_reload_vscode_family_ide("cursor", project=tmp_path)
    assert reopen_calls == [tmp_path]
    assert outcome.ok is True
    assert outcome.method == "reuse_window"


def test_try_open_new_window_when_opted_in(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_AUTO_RELOAD_IDE", "1")
    monkeypatch.setenv("KORU_AUTOPILOT_NEW_WINDOW_RELOAD", "1")
    monkeypatch.setattr(ide_reload, "_resolve_editor_cli", lambda _ide: "/bin/echo")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], *, timeout: float = 15.0):
        calls.append(argv)
        return mock.Mock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(ide_reload, "_run", fake_run)
    outcome = ide_reload.try_open_vscode_family_ide_new_window(
        "vscodium",
        project=tmp_path,
    )
    assert outcome.ok is True
    assert outcome.method == "new_window"
    assert calls == [["/bin/echo", "-n", str(tmp_path.resolve())]]


def test_detect_reload_command_reports_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_AUTO_RELOAD_IDE", "0")
    method, reason = ide_reload.detect_reload_command("vscode", dry_run=False)
    assert method is None
    assert reason == "auto reload disabled"


def test_apply_temporary_repair_reload_env_enables_palette_on_wayland(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", raising=False)
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: False)
    monkeypatch.setattr(ide_reload, "_on_wayland", lambda: True)

    snapshot = ide_reload.apply_temporary_repair_reload_env(same_workspace=False)
    try:
        assert os.environ.get("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD") == "1"
        assert os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD") is None
    finally:
        ide_reload.restore_reload_env(snapshot)

    assert os.environ.get("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD") is None


def test_apply_temporary_repair_reload_env_same_workspace_enables_reuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", raising=False)
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: False)
    monkeypatch.setattr(ide_reload, "_on_wayland", lambda: False)

    snapshot = ide_reload.apply_temporary_repair_reload_env(same_workspace=True)
    try:
        assert os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD") == "1"
    finally:
        ide_reload.restore_reload_env(snapshot)


def test_apply_temporary_repair_reload_env_skips_integrated_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", raising=False)
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: True)
    monkeypatch.setattr(ide_reload, "_on_wayland", lambda: True)

    assert ide_reload.apply_temporary_repair_reload_env(same_workspace=True) is None
    assert os.environ.get("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD") is None
    assert os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD") is None


def test_detect_reload_command_blocks_reuse_window_from_integrated_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_AUTO_RELOAD_IDE", "1")
    monkeypatch.setenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", "1")
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: True)
    monkeypatch.setattr(
        ide_reload,
        "config_home_for_ide",
        lambda _ide: Path("/tmp/cursor-config"),
    )
    method, reason = ide_reload.detect_reload_command("cursor", dry_run=False)
    assert method is None
    assert "integrated IDE terminal" in (reason or "")


def test_await_plugin_handshake_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_RELOAD_VERIFY_PLUGIN", raising=False)
    ok, reason = ide_reload.await_plugin_handshake("vscode")
    assert ok is True
    assert reason == "handshake_verification_disabled"


def _fake_os_strategy(
    *,
    ide_reload_module,
    monkeypatch,
    focus_outcome,
    keyboard_tool: str | None = "wtype",
    focus_methods: tuple[str, ...] = (),
) -> mock.Mock:
    """Patch the active OS strategy with a stub for ``ide_reload`` tests.

    The IDE-reload module delegates focus + keyboard injection entirely to
    :func:`gillm.focus.resolve_active_os_strategy`. Tests should patch *that*
    resolver — they must not poke ``shutil.which`` on the module any more
    because the OS-axis is the source of truth for environment probing.
    """
    from gillm.focus.strategy import OsCapabilities

    strategy = mock.Mock()
    strategy.id = "fake-os"
    strategy.label = "Fake OS"
    strategy.capabilities.return_value = OsCapabilities(
        can_focus_window=bool(focus_methods),
        can_inject_keys=keyboard_tool is not None,
        focus_methods=focus_methods,
        keyboard_tool=keyboard_tool,
    )
    strategy.focus_window.return_value = focus_outcome
    strategy.inject_keys.return_value = True
    monkeypatch.setattr(
        ide_reload_module,
        "resolve_active_os_strategy",
        lambda: strategy,
    )
    return strategy


def test_focus_ide_window_delegates_to_os_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_focus_ide_window`` must not branch on the environment itself; it
    asks the OS strategy and surfaces the strategy's chosen method."""
    from gillm.focus.strategy import FocusOutcome

    _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=True, method="wmctrl"),
    )
    ok, method = ide_reload._focus_ide_window("cursor")
    assert ok is True
    assert method == "wmctrl"


def test_focus_ide_window_rejects_integrated_terminal_for_non_vscode_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The integrated-terminal heuristic must only apply to IDEs that actually
    export ``TERM_PROGRAM=vscode``. JetBrains gets focused by xdotool/wmctrl
    only — never by the integrated-terminal alibi."""
    from gillm.focus.strategy import FocusOutcome

    _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=True, method="integrated_terminal"),
    )
    ok, method = ide_reload._focus_ide_window("jetbrains")
    assert ok is False
    assert method == ""


def test_focus_ide_window_accepts_integrated_terminal_for_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gillm.focus.strategy import FocusOutcome

    _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=True, method="integrated_terminal"),
    )
    ok, method = ide_reload._focus_ide_window("cursor")
    assert ok is True
    assert method == "integrated_terminal"


def test_reload_via_command_palette_uses_os_strategy_inject_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All three keyboard steps (palette, type, confirm) must route through
    ``strategy.inject_keys`` — never through tool-specific subprocess calls."""
    from gillm.focus.strategy import FocusOutcome, KeySequence

    strategy = _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=True, method="wmctrl"),
        focus_methods=("wmctrl",),
    )
    monkeypatch.setattr(ide_reload.time, "sleep", lambda *_a: None)
    outcome = ide_reload.reload_via_command_palette("cursor")
    assert outcome.ok is True
    assert strategy.inject_keys.call_count == 3
    sequences = [call.args[0] for call in strategy.inject_keys.call_args_list]
    assert any(
        isinstance(s, KeySequence) and s.modifiers == ("ctrl", "shift") and s.key == "p"
        for s in sequences
    )
    assert any(
        isinstance(s, KeySequence) and s.literal_text == "Developer: Reload Window"
        for s in sequences
    )
    assert any(
        isinstance(s, KeySequence) and s.key == "Return" for s in sequences
    )


def test_reload_via_command_palette_refuses_integrated_terminal_focus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The TERM_PROGRAM=vscode alibi means the shell is inside the IDE, not
    that the command palette will receive literal text. Do not type reload
    commands into the user's terminal."""
    from gillm.focus.strategy import FocusOutcome

    strategy = _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=True, method="integrated_terminal"),
        focus_methods=("integrated_terminal",),
    )

    outcome = ide_reload.reload_via_command_palette("vscodium")

    assert outcome.ok is False
    assert outcome.attempted is True
    assert "refusing command-palette reload from integrated terminal focus" in (
        outcome.detail or ""
    )
    strategy.inject_keys.assert_not_called()


def test_reload_via_command_palette_explains_wayland_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the OS strategy cannot focus, the error message must mention the
    strategy id + which session type was detected so the operator knows the
    next action."""
    from gillm.focus.strategy import FocusOutcome

    _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=False, detail="no usable focus tool"),
        focus_methods=(),
    )
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    outcome = ide_reload.reload_via_command_palette("cursor")
    assert outcome.ok is False
    assert "session=wayland" in (outcome.detail or "")
    assert "strategy=fake-os" in (outcome.detail or "")


def test_reload_via_command_palette_aborts_when_no_keyboard_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the OS strategy can't inject keys at all, reload must not attempt."""
    from gillm.focus.strategy import FocusOutcome

    _fake_os_strategy(
        ide_reload_module=ide_reload,
        monkeypatch=monkeypatch,
        focus_outcome=FocusOutcome(ok=False),
        keyboard_tool=None,
    )
    outcome = ide_reload.reload_via_command_palette("cursor")
    assert outcome.ok is False
    assert outcome.attempted is False
    assert "no keyboard-injection tool" in (outcome.detail or "")


def test_explain_reload_failure_includes_handshake_reason() -> None:
    outcome = ide_reload.IdeReloadOutcome(
        attempted=True,
        ok=False,
        method="command_palette",
        detail="failed to open command palette",
    )
    text = ide_reload.explain_reload_failure(
        ide="vscode",
        method="command_palette",
        reason="reload execution failed",
        outcome=outcome,
        handshake_reason="plugin_handshake_timeout",
    )
    assert "failed to open command palette" in text
    assert "plugin_handshake_timeout" in text
