from __future__ import annotations

from pathlib import Path

from koru.autonomous_daemon import daemon_status_log_summary
from koruide.daemon.metadata import (
    daemon_metadata_path,
    read_daemon_metadata,
    remove_daemon_metadata,
    write_daemon_metadata,
)


def test_daemon_metadata_path_uses_project_sidecar(tmp_path: Path) -> None:
    path = daemon_metadata_path(tmp_path, Path("/run/user/1000/koru-autopilot-vscodium.sock"))
    assert path == tmp_path / ".planfile" / ".koru" / "koru-autopilot-vscodium.daemon.json"


def test_daemon_metadata_roundtrip_and_pid_guard(tmp_path: Path) -> None:
    path = tmp_path / "daemon.json"
    write_daemon_metadata({"pid": 123, "version": "1.2.3"}, path)
    assert read_daemon_metadata(path) == {"pid": 123, "version": "1.2.3"}
    remove_daemon_metadata(path, pid=456)
    assert path.exists()
    remove_daemon_metadata(path, pid=123)
    assert not path.exists()


def test_daemon_status_log_summary_includes_runtime_identity() -> None:
    summary = daemon_status_log_summary(
        {
            "daemon_version": "1.2.3",
            "daemon_pid": 42,
            "daemon": {
                "pid": 42,
                "git_sha": "abc123",
                "python_executable": "/venv/bin/python",
            },
            "plugins": [],
        }
    )
    assert "pid=42" in summary
    assert "version=1.2.3" in summary
    assert "sha=abc123" in summary
    assert "python=/venv/bin/python" in summary
