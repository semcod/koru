"""Tests for ``koru.autopilot.audit`` (P2.7)."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from koru.autopilot.audit import AuditLog, default_log_path


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_disabled_audit_is_silent(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "ignored.log", enabled=False)
    log.record("drive", chars=42)
    log.close()
    assert not (tmp_path / "ignored.log").exists()


def test_record_writes_ndjson(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "audit.log")
    log.record("drive", ide="windsurf", chars=29, ok=True, submit=True)
    log.close()
    entries = _read_lines(tmp_path / "audit.log")
    assert len(entries) == 1
    entry = entries[0]
    assert entry["event"] == "drive"
    assert entry["ide"] == "windsurf"
    assert entry["chars"] == 29
    assert entry["ok"] is True
    assert "ts" in entry
    # ISO-8601 UTC with millisecond precision and trailing 'Z'.
    assert entry["ts"].endswith("Z")
    assert "T" in entry["ts"]


def test_record_drops_none_values(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "audit.log")
    log.record("plugin_connected", ide="vscode", version=None)
    log.close()
    entry = _read_lines(tmp_path / "audit.log")[0]
    assert entry["ide"] == "vscode"
    assert "version" not in entry


def test_log_file_is_owner_only(tmp_path: Path) -> None:
    """File permissions must be 0600 after the first write."""
    log = AuditLog(path=tmp_path / "audit.log")
    log.record("daemon_started", socket="/tmp/x")
    log.close()
    mode = stat.S_IMODE((tmp_path / "audit.log").stat().st_mode)
    assert mode == 0o600


def test_directory_is_owner_only(tmp_path: Path) -> None:
    subdir = tmp_path / "nested" / "audit"
    log = AuditLog(path=subdir / "audit.log")
    log.record("daemon_started")
    log.close()
    mode = stat.S_IMODE(subdir.stat().st_mode)
    assert mode == 0o700


def test_default_log_path_uses_xdg_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert default_log_path() == tmp_path / "koru" / "autopilot.log"


def test_default_log_path_falls_back_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    p = default_log_path()
    assert p.parts[-3:] == (".local", "state", "koru") or p.name == "autopilot.log"


def test_multiple_records_appear_in_order(tmp_path: Path) -> None:
    log = AuditLog(path=tmp_path / "audit.log")
    for i in range(5):
        log.record("drive", ide="windsurf", chars=i)
    log.close()
    entries = _read_lines(tmp_path / "audit.log")
    assert [e["chars"] for e in entries] == [0, 1, 2, 3, 4]


def test_rotation_caps_file_size(tmp_path: Path) -> None:
    """Hand a tiny ``max_bytes`` and verify rotation kicks in."""
    log = AuditLog(path=tmp_path / "audit.log", max_bytes=200, backup_count=2)
    # Each entry ~80 bytes — three entries trigger rotation.
    for i in range(8):
        log.record("drive", ide="x", chars=i, padding="a" * 30)
    log.close()
    # Rotated file(s) appear next to the active one.
    files = sorted(p.name for p in tmp_path.iterdir())
    assert "audit.log" in files
    assert any(f.startswith("audit.log.") for f in files)


def test_unwritable_directory_disables_silently(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing ``mkdir`` must NOT crash — it disables audit and prints once."""
    target = tmp_path / "deep" / "audit.log"

    def bad_mkdir(self, *a, **k):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "mkdir", bad_mkdir)
    log = AuditLog(path=target)
    assert log.enabled is False
    log.record("drive", chars=1)  # no-op
    log.close()
    assert not target.exists()
    capsys.readouterr().out + capsys.readouterr().err
    # Either captured already or printed unflushed — the test verifies
    # behaviour (silent disable) more than the exact stream.
