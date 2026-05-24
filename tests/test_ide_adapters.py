"""Tests for IDE bridge adapters (koru ide doctor)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from koru.ide_adapters import shared
from koru.ide_adapters.bridge import evaluate_bridge, format_bridge_text, gc_stale_sockets_for_lane
from koru.ide_adapters.registry import get_adapter


def test_publisher_trusted_reads_vscdb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "Cursor"
    db_path = config / "User" / "globalStorage" / "state.vscdb"
    db_path.parent.mkdir(parents=True)
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)",
    )
    con.execute(
        "INSERT INTO ItemTable(key, value) VALUES (?, ?)",
        ("extensions.trustedPublishers", json.dumps({"ms-python": {}})),
    )
    con.commit()
    con.close()
    monkeypatch.setattr(shared, "config_home_for_ide", lambda _ide: config)
    assert shared.publisher_trusted("cursor") is False
    assert shared.add_trusted_publisher("cursor", "semcod") is True
    assert shared.publisher_trusted("cursor") is True


def test_untrusted_publisher_hypothesis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shared, "publisher_trusted", lambda _ide: False)
    monkeypatch.setattr(shared, "vscode_core_version", lambda _ide: "1.105.1")
    hyp = shared.untrusted_publisher_hypothesis("cursor")
    assert hyp is not None
    assert hyp.id == "cursor.trustedPublishers.missing"
    assert hyp.confidence >= 0.9


def test_workspace_socket_mismatch(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    (project / ".cursor").mkdir(parents=True)
    (project / ".cursor" / "settings.json").write_text(
        json.dumps({"koruAutopilot.socketPath": "/run/user/1000/koru-autopilot.sock"}),
        encoding="utf-8",
    )
    report = shared.analyze_socket_settings(
        ide="cursor",
        project=project,
        expected_socket="/run/user/1000/koru-autopilot-cursor.sock",
    )
    assert report.mismatch is True
    hyp = shared.settings_mismatch_hypothesis(report)
    assert hyp is not None
    fixed = shared.fix_workspace_socket(
        project=project,
        ide="cursor",
        expected_socket="/run/user/1000/koru-autopilot-cursor.sock",
    )
    assert fixed is not None
    updated = json.loads((project / ".cursor" / "settings.json").read_text(encoding="utf-8"))
    assert updated["koruAutopilot.socketPath"].endswith("koru-autopilot-cursor.sock")


def test_extension_activated_in_exthost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "Cursor"
    log_dir = config / "logs" / "20260524T120000" / "window1" / "exthost"
    log_dir.mkdir(parents=True)
    (log_dir / "exthost.log").write_text(
        "ExtensionService#_doActivateExtension semcod.koru-autopilot-vscode\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(shared, "config_home_for_ide", lambda _ide: config)
    assert shared.extension_activated_in_exthost("cursor") is True


def test_gc_stale_socket_removes_dead_file(tmp_path: Path) -> None:
    keep = tmp_path / "koru-autopilot-cursor.sock"
    stale = tmp_path / "koru-autopilot.sock"
    stale.touch()
    removed = shared.gc_stale_autopilot_sockets(keep=keep, runtime_dir=tmp_path)
    assert str(stale) in removed
    assert keep.exists() or not keep.exists()


def test_evaluate_bridge_no_daemon(tmp_path: Path) -> None:
    sock = tmp_path / "missing.sock"
    status = evaluate_bridge(ide="cursor", socket_path=sock, project=tmp_path)
    assert status.daemon_running is False
    assert not status.ready
    text = format_bridge_text(status, explain=True)
    assert "daemon" in text


def test_get_adapter_cursor() -> None:
    adapter = get_adapter("cursor")
    assert adapter is not None
    assert adapter.ide_id == "cursor"
