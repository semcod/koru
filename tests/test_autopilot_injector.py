"""Tests for the injection backend picker."""

from __future__ import annotations

import subprocess

import pytest

from koru.autopilot.injector import Injector, InjectorError


def _fake_runner(commands: list[list[str]], *, fail_on: list[str] | None = None):
    fail_on = fail_on or []

    def run(cmd: list[str], stdin: str | None) -> subprocess.CompletedProcess[bytes]:
        commands.append(cmd)
        rc = 1 if cmd[0] in fail_on else 0
        return subprocess.CompletedProcess(args=cmd, returncode=rc, stdout=b"", stderr=b"")

    return run


def _which_factory(present: set[str]):
    def which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name in present else None

    return which


def test_select_backend_x11_prefers_xdotool() -> None:
    inj = Injector(session="x11", which=_which_factory({"xdotool", "wtype"}))
    assert inj.select_backend() == "xdotool"


def test_select_backend_wayland_prefers_wtype_over_ydotool() -> None:
    inj = Injector(session="wayland", which=_which_factory({"wtype", "ydotool"}))
    assert inj.select_backend() == "wtype"


def test_select_backend_wayland_falls_back_to_ydotool() -> None:
    inj = Injector(session="wayland", which=_which_factory({"ydotool"}))
    assert inj.select_backend() == "ydotool"


def test_select_backend_unknown_session_without_display_prefers_wayland_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DISPLAY", raising=False)
    inj = Injector(session="", which=_which_factory({"xdotool", "wtype", "ydotool"}))
    assert inj.select_backend() == "wtype"


def test_select_backend_no_tools_returns_none() -> None:
    inj = Injector(session="x11", which=_which_factory(set()))
    assert inj.select_backend() is None


def test_type_text_dry_run_does_not_call_runner() -> None:
    calls: list[list[str]] = []
    inj = Injector(
        session="x11",
        which=_which_factory({"xdotool"}),
        runner=_fake_runner(calls),
    )
    result = inj.type_text("hello", ide="vscode", dry_run=True)
    assert result.dry_run is True
    assert result.backend == "xdotool"
    assert calls == []


def test_type_text_xdotool_types_and_submits() -> None:
    calls: list[list[str]] = []
    inj = Injector(
        session="x11",
        which=_which_factory({"xdotool"}),
        runner=_fake_runner(calls),
    )
    result = inj.type_text("hi", ide="vscode", submit=True)
    assert result.backend == "xdotool"
    assert result.submitted is True
    assert calls[0][:2] == ["xdotool", "type"]
    assert "hi" in calls[0]
    assert calls[1][:2] == ["xdotool", "key"]
    assert "Return" in calls[1]


def test_type_text_xdotool_supports_extra_enter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_INJECTOR_EXTRA_ENTER", "1")
    calls: list[list[str]] = []
    inj = Injector(
        session="x11",
        which=_which_factory({"xdotool"}),
        runner=_fake_runner(calls),
    )
    inj.type_text("hi", ide="vscode", submit=True)
    key_calls = [c for c in calls if c[:2] == ["xdotool", "key"]]
    assert len(key_calls) == 2
    monkeypatch.delenv("KORU_INJECTOR_EXTRA_ENTER", raising=False)


def test_type_text_ydotool_uses_configurable_enter_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_YDOTOOL_ENTER_KEYCODE", "96")
    calls: list[list[str]] = []
    inj = Injector(
        session="wayland",
        which=_which_factory({"ydotool"}),
        runner=_fake_runner(calls),
    )
    inj.type_text("hi", ide="vscode", submit=True)
    key_calls = [c for c in calls if c[:2] == ["ydotool", "key"]]
    assert key_calls
    assert "96:1" in key_calls[0]
    assert "96:0" in key_calls[0]
    monkeypatch.delenv("KORU_YDOTOOL_ENTER_KEYCODE", raising=False)


def test_type_text_ydotool_submit_newline_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_YDOTOOL_SUBMIT_MODE", "newline")
    calls: list[list[str]] = []
    inj = Injector(
        session="wayland",
        which=_which_factory({"ydotool"}),
        runner=_fake_runner(calls),
    )
    inj.type_text("hi", ide="vscode", submit=True)
    assert any(c[:3] == ["ydotool", "type", "--"] and c[-1] == "\n" for c in calls)
    assert not any(c[:2] == ["ydotool", "key"] for c in calls)
    monkeypatch.delenv("KORU_YDOTOOL_SUBMIT_MODE", raising=False)


def test_type_text_ydotool_submit_ctrl_enter_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_YDOTOOL_SUBMIT_MODE", "ctrl-enter")
    monkeypatch.setenv("KORU_YDOTOOL_ENTER_KEYCODE", "96")
    monkeypatch.setenv("KORU_YDOTOOL_CTRL_KEYCODE", "29")
    calls: list[list[str]] = []
    inj = Injector(
        session="wayland",
        which=_which_factory({"ydotool"}),
        runner=_fake_runner(calls),
    )
    inj.type_text("hi", ide="vscode", submit=True)
    key_calls = [c for c in calls if c[:2] == ["ydotool", "key"]]
    assert key_calls
    assert key_calls[0][2:] == ["29:1", "96:1", "96:0", "29:0"]
    monkeypatch.delenv("KORU_YDOTOOL_SUBMIT_MODE", raising=False)
    monkeypatch.delenv("KORU_YDOTOOL_ENTER_KEYCODE", raising=False)
    monkeypatch.delenv("KORU_YDOTOOL_CTRL_KEYCODE", raising=False)


def test_type_text_wtype_uses_modifiers_for_jetbrains() -> None:
    calls: list[list[str]] = []
    inj = Injector(
        session="wayland",
        which=_which_factory({"wtype"}),
        runner=_fake_runner(calls),
    )
    inj.type_text("payload", ide="jetbrains", submit=True)
    type_call, key_call = calls
    assert type_call[0] == "wtype"
    assert "payload" in type_call
    # jetbrains → ctrl+Return: press ctrl, send Return, release ctrl
    assert key_call[0] == "wtype"
    assert "-M" in key_call and "ctrl" in key_call
    assert "-k" in key_call and "Return" in key_call


def test_type_text_no_submit_only_types() -> None:
    calls: list[list[str]] = []
    inj = Injector(
        session="x11",
        which=_which_factory({"xdotool"}),
        runner=_fake_runner(calls),
    )
    inj.type_text("hi", submit=False)
    assert len(calls) == 1


def test_type_text_propagates_runner_error() -> None:
    calls: list[list[str]] = []
    inj = Injector(
        session="x11",
        which=_which_factory({"xdotool"}),
        runner=_fake_runner(calls, fail_on=["xdotool"]),
    )
    with pytest.raises(InjectorError, match="all keyboard injection backends failed"):
        inj.type_text("hi")


def test_type_text_empty_raises() -> None:
    inj = Injector(session="x11", which=_which_factory({"xdotool"}))
    with pytest.raises(InjectorError, match="empty text"):
        inj.type_text("")


def test_type_text_no_backend_raises() -> None:
    inj = Injector(session="x11", which=_which_factory(set()))
    with pytest.raises(InjectorError, match="no keyboard injection backend"):
        inj.type_text("hi")


def test_probe_marks_unavailable_when_missing_tool() -> None:
    inj = Injector(session="x11", which=_which_factory({"xdotool"}))
    statuses = {s.name: s for s in inj.probe()}
    assert statuses["xdotool"].available is True
    assert statuses["wtype"].available is False
    assert "not in PATH" in statuses["wtype"].reason


def test_probe_marks_unavailable_on_wrong_session() -> None:
    # wtype is installed but we're on X11 — it shouldn't be reported as usable.
    inj = Injector(session="x11", which=_which_factory({"xdotool", "wtype"}))
    statuses = {s.name: s for s in inj.probe()}
    assert statuses["wtype"].available is False
    assert "wayland" in statuses["wtype"].reason


# ---- R3: _press_wtype fails loud on multi-modifier combos ----


def test_wtype_rejects_multi_modifier_submit_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A future IDE entry using ``ctrl+shift+Return`` must raise, not run."""
    from koru.autopilot import config as config_mod
    from koru.autopilot import injector as injector_mod

    calls: list[list[str]] = []
    inj = Injector(
        session="wayland",
        which=_which_factory({"wtype"}),
        runner=_fake_runner(calls),
    )
    # Inject a config with a multi-modifier mapping and patch the
    # injector-side binding (``injector_mod.cached_config`` is the
    # symbol the resolver actually reads).
    fake_config = config_mod.AutopilotConfig(
        submit_keys={"default": "Return", "evil": "ctrl+shift+Return"},
    )
    monkeypatch.setattr(injector_mod, "cached_config", lambda: fake_config)
    with pytest.raises(InjectorError, match="only single-modifier combos"):
        inj.type_text("hi", ide="evil", submit=True)
    # Type ran, but the failing submit press must not have produced a key call.
    assert len(calls) == 1
    assert calls[0][0] == "wtype"  # the type call


def test_type_text_wayland_falls_back_when_wtype_fails() -> None:
    calls: list[list[str]] = []

    def run(cmd: list[str], stdin: str | None) -> subprocess.CompletedProcess[bytes]:
        calls.append(cmd)
        if cmd[0] == "wtype":
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout=b"",
                stderr=b"wtype failed",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")

    inj = Injector(
        session="wayland",
        which=_which_factory({"wtype", "ydotool"}),
        runner=run,
    )
    result = inj.type_text("hi", ide="vscode", submit=False)
    assert result.backend == "ydotool"
    assert calls[0][0] == "wtype"
    assert any(c[0] == "ydotool" for c in calls)


def test_injector_forced_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_INJECTOR_BACKEND", "ydotool")
    inj = Injector(session="wayland", which=_which_factory({"wtype", "ydotool"}))
    assert inj._candidate_backends() == ["ydotool"]
    monkeypatch.delenv("KORU_INJECTOR_BACKEND", raising=False)


def test_wtype_single_modifier_still_works() -> None:
    calls: list[list[str]] = []
    inj = Injector(
        session="wayland",
        which=_which_factory({"wtype"}),
        runner=_fake_runner(calls),
    )
    inj.type_text("payload", ide="jetbrains", submit=True)
    _, key_call = calls
    assert key_call[:2] == ["wtype", "-M"]
