from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from koru.autopilot.os_injector import (
    OsInjectorError,
    OsInjectorProfile,
    capture_from_xdotool,
    inject_with_profile,
    iter_config_paths,
    load_profile,
    profile_from_mouse,
    save_profile,
    try_drive_with_profile,
    try_load_profile,
)


def test_save_and_load_profile(tmp_path: Path) -> None:
    config = tmp_path / "profiles.json"
    profile = OsInjectorProfile(tool_id="windsurf", chat_x=222, chat_y=333)
    save_profile(profile, config_path=config)
    loaded = load_profile("windsurf", config_path=config)
    assert loaded == profile
    payload = json.loads(config.read_text(encoding="utf-8"))
    assert "window_id" not in payload["windsurf"]
    assert payload["windsurf"] == {"chat_x": 222, "chat_y": 333}


def test_load_profile_accepts_legacy_window_id(tmp_path: Path) -> None:
    config = tmp_path / "p.json"
    config.write_text(
        json.dumps({"cursor": {"window_id": 99, "chat_x": 1, "chat_y": 2}}),
        encoding="utf-8",
    )
    p = load_profile("cursor", config_path=config)
    assert p.window_id == 99
    assert p.chat_x == 1


def test_profile_from_mouse_builds_profile() -> None:
    p = profile_from_mouse("windsurf", x=10, y=20)
    assert p == OsInjectorProfile(tool_id="windsurf", chat_x=10, chat_y=20)


def test_capture_from_xdotool_parses_shell_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            args=a[0],
            returncode=0,
            stdout="X=100\nY=200\nSCREEN=0\nWINDOW=300\n",
            stderr="",
        ),
    )
    window_id, x, y = capture_from_xdotool()
    assert (window_id, x, y) == (0, 100, 200)


def test_inject_with_profile_paste_path_uses_clipboard_then_ctrl_v(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import koru.autopilot.os_injector as oi

    calls: list[list[str]] = []

    def _run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(oi.time, "sleep", lambda _s: None)
    monkeypatch.setattr(oi.shutil, "which", lambda n: f"/bin/{n}")
    monkeypatch.setattr(oi, "_is_wayland_session", lambda: False)
    monkeypatch.setenv("KORU_OS_INJECTOR_INPUT", "paste")
    out = inject_with_profile(
        profile=OsInjectorProfile(tool_id="cursor", chat_x=20, chat_y=30),
        text="hello",
        submit=True,
        dry_run=False,
    )
    assert out["ok"] is True
    assert out["input_method"] == "paste"
    joined = "\n".join(" ".join(c) for c in calls)
    assert "windowactivate" not in joined
    assert calls[0][:3] == ["xdotool", "mousemove", "20"]
    assert calls[1][:2] == ["xdotool", "click"]
    assert any(c[:2] == ["/bin/xclip", "-selection"] for c in calls)
    assert any("ctrl+v" in " ".join(c) for c in calls)


def test_inject_with_profile_type_fallback_when_no_clip_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import koru.autopilot.os_injector as oi

    calls: list[list[str]] = []

    def _run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(oi.time, "sleep", lambda _s: None)
    monkeypatch.setattr(oi.shutil, "which", lambda n: "/xdotool" if n == "xdotool" else None)
    monkeypatch.setattr(oi, "_is_wayland_session", lambda: False)
    monkeypatch.setenv("KORU_OS_INJECTOR_INPUT", "type")
    out = inject_with_profile(
        profile=OsInjectorProfile(tool_id="cursor", chat_x=5, chat_y=6),
        text="hi",
        submit=False,
        dry_run=False,
    )
    assert out["input_method"] == "type"
    assert calls[0][1:3] == ["mousemove", "5"]
    assert calls[1][:2] == ["xdotool", "click"]
    assert calls[2][:2] == ["xdotool", "type"]


def test_load_profile_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(OsInjectorError, match="missing profile"):
        load_profile("vscode", config_path=tmp_path / "nope.json")


def test_inject_with_profile_paste_timeout_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import koru.autopilot.os_injector as oi

    def _run(cmd, **kwargs):
        if cmd and cmd[0] == "/bin/xclip":
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=2.0)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(oi.time, "sleep", lambda _s: None)
    monkeypatch.setattr(oi.shutil, "which", lambda n: f"/bin/{n}")
    monkeypatch.setattr(oi, "_is_wayland_session", lambda: False)
    monkeypatch.setenv("KORU_OS_INJECTOR_INPUT", "paste")
    with pytest.raises(OsInjectorError, match="xclip timed out"):
        inject_with_profile(
            profile=OsInjectorProfile(tool_id="windsurf", chat_x=1, chat_y=2),
            text="hello",
            submit=True,
            dry_run=False,
        )


def test_try_load_profile_prefers_project_over_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proj_cfg = tmp_path / ".koru" / "ide-os-injector.json"
    proj_cfg.parent.mkdir(parents=True)
    proj_cfg.write_text(
        json.dumps({"cursor": {"chat_x": 2, "chat_y": 3}}),
        encoding="utf-8",
    )
    other = tmp_path / "sub"
    other.mkdir()
    cwd_cfg = other / ".koru" / "ide-os-injector.json"
    cwd_cfg.parent.mkdir(parents=True)
    cwd_cfg.write_text(
        json.dumps({"cursor": {"chat_x": 8, "chat_y": 7}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(other)
    loaded = try_load_profile("cursor", project=tmp_path)
    assert loaded is not None
    assert loaded.chat_x == 2


def test_iter_config_paths_dedupes_project_and_cwd(tmp_path: Path) -> None:
    resolved = tmp_path.resolve()
    paths = iter_config_paths(project=resolved)
    assert len(paths) == len({str(p.resolve()) for p in paths})


def test_try_drive_with_profile_skips_saved_profile_on_wayland_without_ydotool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import koru.autopilot.os_injector as oi

    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.delenv("KORU_OS_INJECTOR", raising=False)
    monkeypatch.setattr(oi.shutil, "which", lambda _n: "/xdotool" if _n == "xdotool" else None)
    cfg = tmp_path / ".koru" / "ide-os-injector.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps({"cursor": {"chat_x": 2, "chat_y": 3}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    out = try_drive_with_profile(
        tool_id="cursor", text="x", submit=False, project=None, cli_dry_run=False
    )
    assert out is None


def test_try_drive_with_profile_uses_saved_profile_on_wayland_with_ydotool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: calibrated chat coordinates must work on Wayland via ydotool
    without requiring KORU_OS_INJECTOR=1 — otherwise JetBrains drive types into
    the file editor because try_drive_with_profile is skipped."""
    import koru.autopilot.os_injector as oi

    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.delenv("KORU_OS_INJECTOR", raising=False)
    monkeypatch.setattr(
        oi.shutil,
        "which",
        lambda n: "/usr/bin/ydotool" if n == "ydotool" else None,
    )
    cfg = tmp_path / ".koru" / "ide-os-injector.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"jetbrains": {"chat_x": 9, "chat_y": 10}}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    out = try_drive_with_profile(
        tool_id="jetbrains",
        text="x",
        submit=False,
        project=None,
        cli_dry_run=True,
    )
    assert out is not None
    assert out["backend"] == "os_injector"
    assert out["chat_x"] == 9


def test_try_drive_with_profile_forced_works_on_wayland(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import koru.autopilot.os_injector as oi

    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("KORU_OS_INJECTOR", "1")
    monkeypatch.setattr(oi.shutil, "which", lambda _n: "/xdotool")
    cfg = tmp_path / ".koru" / "ide-os-injector.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"cursor": {"chat_x": 2, "chat_y": 3}}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    out = try_drive_with_profile(
        tool_id="cursor", text="x", submit=False, project=None, cli_dry_run=True
    )
    assert out is not None
    assert out["backend"] == "os_injector"


def test_try_drive_with_profile_skips_when_env_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    import koru.autopilot.os_injector as oi

    monkeypatch.setenv("KORU_OS_INJECTOR", "0")
    monkeypatch.setattr(oi.shutil, "which", lambda _n: "/xdotool")
    assert (
        try_drive_with_profile(
            tool_id="cursor",
            text="hi",
            submit=True,
            project=None,
        )
        is None
    )


def test_try_drive_with_profile_uses_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import koru.autopilot.os_injector as oi

    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.setattr(oi.shutil, "which", lambda _n: "/xdotool")
    cfg = tmp_path / ".koru" / "ide-os-injector.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps({"cursor": {"chat_x": 2, "chat_y": 3}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    out = try_drive_with_profile(
        tool_id="cursor",
        text="x",
        submit=False,
        project=None,
        cli_dry_run=True,
    )
    assert out is not None
    assert out["backend"] == "os_injector"
    assert out["dry_run"] is True


def test_inject_post_focus_delay_env_controls_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import koru.autopilot.os_injector as oi

    calls: list[list[str]] = []
    sleeps: list[float] = []

    def _run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(oi.time, "sleep", lambda s: sleeps.append(float(s)))
    monkeypatch.setattr(oi.shutil, "which", lambda n: f"/bin/{n}")
    monkeypatch.setenv("KORU_OS_INJECTOR_INPUT", "paste")
    monkeypatch.setenv("KORU_OS_INJECTOR_POST_FOCUS_DELAY", "0.25")
    inject_with_profile(
        profile=OsInjectorProfile(tool_id="cursor", chat_x=1, chat_y=2),
        text="x",
        submit=False,
        dry_run=False,
    )
    assert sleeps == [0.25]


def test_inject_post_focus_delay_zero_skips_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import koru.autopilot.os_injector as oi

    calls: list[list[str]] = []

    def _run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(oi.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("sleep")))
    monkeypatch.setattr(oi.shutil, "which", lambda n: f"/bin/{n}")
    monkeypatch.setenv("KORU_OS_INJECTOR_INPUT", "paste")
    monkeypatch.setenv("KORU_OS_INJECTOR_POST_FOCUS_DELAY", "0")
    inject_with_profile(
        profile=OsInjectorProfile(tool_id="cursor", chat_x=1, chat_y=2),
        text="x",
        submit=False,
        dry_run=False,
    )
