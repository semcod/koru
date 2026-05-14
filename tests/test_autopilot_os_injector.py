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
    save_profile,
    try_drive_with_profile,
    try_load_profile,
)


def test_save_and_load_profile(tmp_path: Path) -> None:
    config = tmp_path / "profiles.json"
    profile = OsInjectorProfile(tool_id="windsurf", window_id=11, chat_x=222, chat_y=333)
    save_profile(profile, config_path=config)
    loaded = load_profile("windsurf", config_path=config)
    assert loaded == profile
    payload = json.loads(config.read_text(encoding="utf-8"))
    assert payload["windsurf"]["window_id"] == 11


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
    assert (window_id, x, y) == (300, 100, 200)


def test_inject_with_profile_runs_expected_xdotool_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def _run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)
    out = inject_with_profile(
        profile=OsInjectorProfile(tool_id="cursor", window_id=77, chat_x=20, chat_y=30),
        text="hello",
        submit=True,
        dry_run=False,
    )
    assert out["ok"] is True
    assert calls[0][:2] == ["xdotool", "mousemove"]
    assert calls[1][:2] == ["xdotool", "type"]
    assert calls[2][:2] == ["xdotool", "key"]


def test_inject_with_profile_focus_window_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def _run(cmd, **kwargs):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setenv("KORU_OS_INJECTOR_FOCUS_WINDOW", "1")
    monkeypatch.setattr(subprocess, "run", _run)
    out = inject_with_profile(
        profile=OsInjectorProfile(tool_id="cursor", window_id=77, chat_x=20, chat_y=30),
        text="hello",
        submit=False,
        dry_run=False,
    )
    assert out["ok"] is True
    assert calls[0][:3] == ["xdotool", "windowactivate", "--sync"]


def test_load_profile_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(OsInjectorError, match="missing profile"):
        load_profile("vscode", config_path=tmp_path / "nope.json")


def test_try_load_profile_prefers_project_over_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    proj_cfg = tmp_path / ".koru" / "ide-os-injector.json"
    proj_cfg.parent.mkdir(parents=True)
    proj_cfg.write_text(
        json.dumps({"cursor": {"window_id": 1, "chat_x": 2, "chat_y": 3}}),
        encoding="utf-8",
    )
    other = tmp_path / "sub"
    other.mkdir()
    cwd_cfg = other / ".koru" / "ide-os-injector.json"
    cwd_cfg.parent.mkdir(parents=True)
    cwd_cfg.write_text(
        json.dumps({"cursor": {"window_id": 9, "chat_x": 8, "chat_y": 7}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(other)
    loaded = try_load_profile("cursor", project=tmp_path)
    assert loaded is not None
    assert loaded.window_id == 1


def test_iter_config_paths_dedupes_project_and_cwd(tmp_path: Path) -> None:
    resolved = tmp_path.resolve()
    paths = iter_config_paths(project=resolved)
    assert len(paths) == len({str(p.resolve()) for p in paths})


def test_try_drive_with_profile_works_when_xdg_session_type_wayland(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: Wayland session must not hide a working xdotool + profile path."""
    import koru.autopilot.os_injector as oi

    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(oi.shutil, "which", lambda _n: "/xdotool")
    cfg = tmp_path / ".koru" / "ide-os-injector.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps({"cursor": {"window_id": 1, "chat_x": 2, "chat_y": 3}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    out = try_drive_with_profile(
        tool_id="cursor", text="x", submit=False, project=None, cli_dry_run=True,
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


def test_try_drive_with_profile_uses_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import koru.autopilot.os_injector as oi

    monkeypatch.setattr(oi.shutil, "which", lambda _n: "/xdotool")
    cfg = tmp_path / ".koru" / "ide-os-injector.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps({"cursor": {"window_id": 1, "chat_x": 2, "chat_y": 3}}),
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
