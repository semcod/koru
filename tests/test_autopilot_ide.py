"""Tests for IDE process detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from koru.autopilot import ide as ide_mod


@pytest.fixture
def fake_proc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a tiny ``/proc``-like tree under ``tmp_path`` with two PIDs."""

    def write_pid(pid: int, comm: str, cmdline: list[str]) -> None:
        d = tmp_path / str(pid)
        d.mkdir()
        (d / "comm").write_text(comm + "\n")
        (d / "cmdline").write_bytes(b"\x00".join(c.encode() for c in cmdline) + b"\x00")

    write_pid(1234, "windsurf", ["/opt/windsurf/windsurf", "--type=renderer"])
    write_pid(5678, "java", ["/usr/lib/jvm/java/bin/java", "-jar", "/opt/idea/lib/idea.jar"])
    write_pid(9999, "bash", ["bash"])  # noise — must not match any IDE

    def fake_read_comm(pid: int) -> str:
        return (tmp_path / str(pid) / "comm").read_text().strip()

    def fake_read_cmdline(pid: int) -> str:
        raw = (tmp_path / str(pid) / "cmdline").read_bytes()
        return raw.replace(b"\x00", b" ").decode().strip()

    monkeypatch.setattr(ide_mod, "_read_comm", fake_read_comm)
    monkeypatch.setattr(ide_mod, "_read_cmdline", fake_read_cmdline)
    return tmp_path


def test_detect_running_ides_finds_windsurf_and_jetbrains(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678, 9999])
    ids = [d.id for d in detected]
    assert "windsurf" in ids
    assert "jetbrains" in ids
    assert "vscode" not in ids


def test_detect_running_ides_deduplicates_same_ide(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 1234])
    assert sum(1 for d in detected if d.id == "windsurf") == 1


def test_detect_running_ides_skips_unknown_processes(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[9999])
    assert detected == []


def test_pick_target_prefers_user_choice(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    chosen = ide_mod.pick_target(detected, prefer="jetbrains")
    assert chosen is not None
    assert chosen.id == "jetbrains"


def test_pick_target_returns_none_when_pref_not_running(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234])
    chosen = ide_mod.pick_target(detected, prefer="vscode")
    assert chosen is None


def test_pick_target_defaults_to_first(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[5678, 1234])
    chosen = ide_mod.pick_target(detected)
    # windsurf comes first in declared order, regardless of pid order.
    assert chosen is not None
    assert chosen.id == "windsurf"


def test_pick_target_empty_list_returns_none() -> None:
    assert ide_mod.pick_target([]) is None
