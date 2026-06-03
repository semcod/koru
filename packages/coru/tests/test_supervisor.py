from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from coru.supervisor.models import LaneRecord
from coru.supervisor.http_server import SupervisorHTTPServer
from coru.supervisor.probe import probe_lane_health
from coru.supervisor.registry import active_lane_pair, load_registry, register_lane, set_active_lane
from coru.supervisor.service import SupervisorService
from coru.supervisor.socket_path import socket_basename


def test_socket_basename() -> None:
    assert socket_basename("cursor-main") == "koru-autopilot-cursor-main.sock"


def test_register_lane_and_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORU_SUPERVISOR_STATE_DIR", str(tmp_path))
    project = tmp_path / "koru"
    project.mkdir()
    record = register_lane(
        ide="cursor",
        instance="cursor-main",
        project=str(project),
        set_active=True,
    )
    assert record.ide == "cursor"
    assert record.instance == "cursor-main"
    assert "cursor-main.sock" in record.socket_path
    assert active_lane_pair() == ("cursor", "cursor-main")
    registry = load_registry()
    assert registry.active_lane == "cursor-main"
    set_active_lane("cursor-main")
    assert load_registry().active_lane == "cursor-main"


def test_probe_lane_health_daemon_down() -> None:
    def fake_run(*_args, **_kwargs):
        class Proc:
            returncode = 1
            stdout = ""
            stderr = "daemon is NOT running"

        return Proc()

    record = LaneRecord(
        ide="cursor",
        instance="cursor-main",
        socket_path="/tmp/koru-autopilot-cursor-main.sock",
    )
    health = probe_lane_health(record, koru_argv=["koru"], run=fake_run)
    assert health.daemon_running is False
    assert health.plugin_connected is False
    assert health.issues


def test_probe_lane_health_with_plugin() -> None:
    payload = {
        "daemon": {"version": "0.1.309"},
        "plugins": [{"ide": "cursor", "version": "0.2.1", "build": "abc123"}],
        "expected_plugin_build": "abc123",
    }

    def fake_run(*_args, **_kwargs):
        class Proc:
            returncode = 0
            stdout = json.dumps(payload)
            stderr = ""

        return Proc()

    record = LaneRecord(
        ide="cursor",
        instance="cursor-main",
        socket_path="/tmp/koru-autopilot-cursor-main.sock",
    )
    health = probe_lane_health(record, koru_argv=["koru"], run=fake_run)
    assert health.daemon_running is True
    assert health.plugin_connected is True
    assert health.plugin_count == 1
    assert health.plugin_version == "0.2.1"


def test_supervisor_cli_register(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("CORU_SUPERVISOR_STATE_DIR", str(tmp_path))
    from coru.supervisor.cli import main as supervisor_main

    rc = supervisor_main(["register", "cursor", "cursor-main", "--set-active"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "cursor-main" in out


def test_register_lane_rejects_missing_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORU_SUPERVISOR_STATE_DIR", str(tmp_path))
    from coru.supervisor.registry import register_lane

    with pytest.raises(FileNotFoundError, match="project directory does not exist"):
        register_lane(
            ide="cursor",
            instance="cursor-main",
            project=str(tmp_path / "missing"),
            set_active=True,
        )


def test_supervisor_cli_install_unit_print_only(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from coru.supervisor.cli import main as supervisor_main

    monkeypatch.setattr("coru.supervisor.systemd_unit.resolve_coru_bin", lambda: "/usr/bin/coru")
    rc = supervisor_main(["install-unit", "--print-only"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "[Service]" in out
    assert "ExecStart=/usr/bin/coru supervisor start --foreground --refresh-interval 30" in out


def test_supervisor_cli_install_unit_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from coru.supervisor.cli import main as supervisor_main

    dest = tmp_path / "coru-supervisor.service"
    monkeypatch.setattr("coru.supervisor.systemd_unit.resolve_coru_bin", lambda: "/usr/bin/coru")
    rc = supervisor_main(["install-unit", "--dest", str(dest)])

    assert rc == 0
    assert dest.is_file()
    content = dest.read_text(encoding="utf-8")
    assert "ExecStart=/usr/bin/coru supervisor start --foreground --refresh-interval 30" in content


def test_service_reconnect_lane_restarts_daemon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORU_SUPERVISOR_STATE_DIR", str(tmp_path))
    register_lane(ide="cursor", instance="cursor-main", project=str(tmp_path), set_active=True)

    calls: list[str] = []

    def fake_stop(record, *, koru_argv=None):
        calls.append(f"stop:{record.instance}")
        return True, "stopped"

    def fake_start(record, *, koru_argv=None):
        calls.append(f"start:{record.instance}")
        return True, "started"

    monkeypatch.setattr("coru.supervisor.service.stop_daemon", fake_stop)
    monkeypatch.setattr("coru.supervisor.service.start_daemon", fake_start)
    monkeypatch.setattr(SupervisorService, "refresh_lane_health", lambda self, record: record.health)

    service = SupervisorService(registry_file=tmp_path / "supervisor.json", koru_argv=["koru"])
    ok, detail = service.reconnect_lane("cursor-main")

    assert ok is True
    assert "reconnected" in detail
    assert calls == ["stop:cursor-main", "start:cursor-main"]


def test_supervisor_http_reconnect_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORU_SUPERVISOR_STATE_DIR", str(tmp_path))

    class _ServiceStub:
        registry_path = tmp_path / "supervisor.json"
        verbose = False
        pid = 1234
        url = "http://127.0.0.1:8766"

        def reconnect_lane(self, instance: str):
            return True, f"reconnected:{instance}"

    service = _ServiceStub()
    server = SupervisorHTTPServer(service, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        req = urllib.request.Request(
            f"http://{server.host}:{server.port}/api/lanes/cursor-main/reconnect",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True
        assert payload["instance"] == "cursor-main"
        assert payload["detail"] == "reconnected:cursor-main"
    finally:
        server.shutdown()
        thread.join(timeout=2.0)


def test_supervisor_cli_reconnect(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from coru.supervisor.cli import main as supervisor_main

    monkeypatch.setattr(
        SupervisorService,
        "reconnect_lane",
        lambda self, instance: (True, f"reconnected:{instance}"),
    )
    rc = supervisor_main(["reconnect", "cursor-main"])

    assert rc == 0
    assert "reconnected:cursor-main" in capsys.readouterr().out
