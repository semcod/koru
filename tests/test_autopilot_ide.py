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


# ---- R13: focused-window arbitration ----


def test_detect_focused_ide_id_from_active_pid(fake_proc: Path) -> None:
    # PID 5678 is our fake JetBrains java process in the fixture.
    assert ide_mod.detect_focused_ide_id(_active_pid=5678) == "jetbrains"


def test_detect_focused_ide_id_returns_none_for_unknown_pid(fake_proc: Path) -> None:
    assert ide_mod.detect_focused_ide_id(_active_pid=9999) is None


def test_focused_ide_returns_matching_instance(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    focused = ide_mod.focused_ide(detected, focused_id="jetbrains")
    assert focused is not None
    assert focused.id == "jetbrains"


def test_pick_target_prefers_focused_when_no_explicit_prefer(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    chosen = ide_mod.pick_target(detected, focused_id="jetbrains")
    assert chosen is not None
    assert chosen.id == "jetbrains"


def test_pick_target_explicit_prefer_beats_focus(fake_proc: Path) -> None:
    detected = ide_mod.detect_running_ides(_pids=[1234, 5678])
    chosen = ide_mod.pick_target(detected, prefer="windsurf", focused_id="jetbrains")
    assert chosen is not None
    assert chosen.id == "windsurf"


# ---- R5: detect_running_ides_cached ----


def test_detect_cached_uses_cache_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Second call within ``ttl`` must NOT trigger a fresh ``/proc`` scan."""
    ide_mod.clear_detect_cache()
    calls: list[None] = []

    def fake_detect(*, _pids: list[int] | None = None) -> list:
        calls.append(None)
        return []

    monkeypatch.setattr(ide_mod, "detect_running_ides", fake_detect)
    ide_mod.detect_running_ides_cached(ttl=10.0)
    ide_mod.detect_running_ides_cached(ttl=10.0)
    ide_mod.detect_running_ides_cached(ttl=10.0)
    assert len(calls) == 1


def test_detect_cached_ttl_zero_always_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    ide_mod.clear_detect_cache()
    calls: list[None] = []
    monkeypatch.setattr(
        ide_mod, "detect_running_ides", lambda **_: (calls.append(None) or [])
    )
    ide_mod.detect_running_ides_cached(ttl=0)
    ide_mod.detect_running_ides_cached(ttl=0)
    assert len(calls) == 2


def test_clear_detect_cache_forces_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    ide_mod.clear_detect_cache()
    calls: list[None] = []
    monkeypatch.setattr(
        ide_mod, "detect_running_ides", lambda **_: (calls.append(None) or [])
    )
    ide_mod.detect_running_ides_cached(ttl=10.0)
    ide_mod.clear_detect_cache()
    ide_mod.detect_running_ides_cached(ttl=10.0)
    assert len(calls) == 2
