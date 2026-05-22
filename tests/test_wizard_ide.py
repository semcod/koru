"""Unit tests for IDE install-path detection and merge with running processes."""

from __future__ import annotations

from pathlib import Path

from koru.wizard.ide import (
    DetectedIDE,
    discover_installed_ides,
    summarize_ides,
)
from koruide.ide import RunningIDE


def _hint_for(path: Path) -> dict[str, tuple[str, tuple[str, ...]]]:
    return {"cursor": ("Cursor", (str(path),))}


def test_discover_marks_installed_ides_as_not_running(tmp_path: Path) -> None:
    fake_cursor = tmp_path / "cursor"
    fake_cursor.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_cursor.chmod(0o755)

    result = discover_installed_ides(hint_map=_hint_for(fake_cursor), running_override=[])

    assert [(ide.id, ide.running, ide.pid) for ide in result] == [("cursor", False, None)]
    assert result[0].path == str(fake_cursor)


def test_discover_promotes_to_running_when_process_seen(tmp_path: Path) -> None:
    fake_cursor = tmp_path / "cursor"
    fake_cursor.write_text("ok", encoding="utf-8")
    running = [RunningIDE(id="cursor", label="Cursor", pid=4321, exe="/opt/Cursor/cursor")]

    result = discover_installed_ides(hint_map=_hint_for(fake_cursor), running_override=running)

    assert result[0].id == "cursor"
    assert result[0].running is True
    assert result[0].pid == 4321
    assert result[0].path == "/opt/Cursor/cursor"


def test_discover_keeps_running_only_ides(tmp_path: Path) -> None:
    running = [RunningIDE(id="windsurf", label="Windsurf", pid=99, exe="/opt/windsurf/windsurf")]

    result = discover_installed_ides(hint_map={"cursor": ("Cursor", ())}, running_override=running)

    assert any(ide.id == "windsurf" and ide.running for ide in result)


def test_discover_returns_empty_when_no_signals() -> None:
    result = discover_installed_ides(hint_map={}, running_override=[])
    assert result == []


def test_summarize_handles_empty_list() -> None:
    text = summarize_ides([])
    assert "no IDEs detected" in text


def test_summarize_lists_running_first() -> None:
    installed = DetectedIDE(
        id="cursor", label="Cursor", running=False, pid=None, path="/opt/cursor"
    )
    running = DetectedIDE(
        id="vscode", label="VS Code", running=True, pid=7, path="/usr/bin/code"
    )
    text = summarize_ides([installed, running])
    lines = text.splitlines()
    assert "VS Code" in lines[0] or "running pid=7" in lines[0]
