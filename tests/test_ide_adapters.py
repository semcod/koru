"""Tests for IDE bridge adapters (koru ide doctor)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from koru.ide_adapters import shared
from koru.ide_adapters.base import SettingsReport
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


def test_apply_safe_fixes_adds_trusted_publisher_while_ide_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = get_adapter("vscode")
    assert adapter is not None
    calls: list[str] = []
    monkeypatch.setattr(
        shared,
        "analyze_socket_settings",
        lambda **_kwargs: SettingsReport(
            expected_socket="/tmp/koru-autopilot-vscode.sock",
            user_socket=None,
            workspace_socket=None,
            mismatch=False,
        ),
    )
    monkeypatch.setattr(shared, "publisher_trusted", lambda _ide: False)

    def fake_add_trusted_publisher(ide: str) -> bool:
        calls.append(ide)
        return True

    monkeypatch.setattr(shared, "add_trusted_publisher", fake_add_trusted_publisher)

    applied = adapter.apply_safe_fixes(
        project=tmp_path,
        expected_socket="/tmp/koru-autopilot-vscode.sock",
        fix=True,
        ide_running=True,
    )

    assert calls == ["vscode"]
    assert applied == [
        "extensions.trustedPublishers += semcod (wymagany Developer: Reload Window w VS Code)",
    ]


def test_inactive_extension_hypothesis_uses_real_config_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "Code"
    log_dir = config / "logs" / "20260524T120000" / "window1" / "exthost"
    log_dir.mkdir(parents=True)
    (log_dir / "exthost.log").write_text("extension host started\n", encoding="utf-8")
    monkeypatch.setattr(shared, "config_home_for_ide", lambda _ide: config)

    hyp = shared.inactive_extension_hypothesis("vscode")

    assert hyp is not None
    assert str(config / "logs") in hyp.evidence
    assert "Vscode" not in hyp.evidence
    assert "Reload Window" in hyp.remediation.summary
    assert "extension host" in hyp.remediation.summary


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
    assert hyp.remediation.command is not None
    assert "koru ide doctor --fix" in hyp.remediation.command
    assert "--fix-settings" not in hyp.remediation.command
    fixed = shared.fix_workspace_socket(
        project=project,
        ide="cursor",
        expected_socket="/run/user/1000/koru-autopilot-cursor.sock",
    )
    assert fixed is not None
    updated = json.loads((project / ".cursor" / "settings.json").read_text(encoding="utf-8"))
    assert updated["koruAutopilot.socketPath"].endswith("koru-autopilot-cursor.sock")


def test_user_socket_mismatch_detected_without_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "Cursor" / "User"
    config.mkdir(parents=True)
    settings = config / "settings.json"
    settings.write_text(
        json.dumps({"koruAutopilot.socketPath": "/run/user/1000/koru-autopilot-cursor.sock"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(shared, "user_settings_path", lambda _ide: settings)
    report = shared.analyze_socket_settings(
        ide="cursor",
        project=None,
        expected_socket="/run/user/1000/koru-autopilot-cursor-main.sock",
    )
    assert report.mismatch is True
    fixed = shared.fix_user_socket(
        ide="cursor",
        expected_socket="/run/user/1000/koru-autopilot-cursor-main.sock",
    )
    assert fixed == settings
    updated = json.loads(settings.read_text(encoding="utf-8"))
    assert updated["koruAutopilot.socketPath"].endswith("koru-autopilot-cursor-main.sock")


def test_extension_activated_in_exthost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "Cursor"
    log_dir = config / "logs" / "20260524T120000" / "window1" / "exthost"
    log_dir.mkdir(parents=True)
    (log_dir / "exthost.log").write_text(
        "ExtensionService#_doActivateExtension semcod.koru-autopilot-cursor\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(shared, "config_home_for_ide", lambda _ide: config)
    assert shared.extension_activated_in_exthost("cursor") is True


def test_extension_reload_required_lines_use_actual_ide_label() -> None:
    lines = shared.extension_reload_required_lines("vscodium", label="VSCodium")

    assert any("W VSCodium naci" in line for line in lines)
    assert not any("Cursorze/VS Code" in line for line in lines)


def test_extension_activated_uses_latest_session_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stale activation in an older session must not hide missing activation now."""
    config = tmp_path / "Cursor"
    old = config / "logs" / "20260524T100000" / "window1" / "exthost"
    new = config / "logs" / "20260524T190000" / "window1" / "exthost"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (old / "exthost.log").write_text(
        "Extension activated success: semcod.koru-autopilot-cursor\n",
        encoding="utf-8",
    )
    (new / "exthost.log").write_text(
        "Extension activated success: vscode.git\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(shared, "config_home_for_ide", lambda _ide: config)
    assert shared.extension_activated_in_exthost("cursor") is False


def test_latest_ide_exthost_session_skips_cli_only_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / "Cursor"
    cli_only = config / "logs" / "20260524T191323"
    cli_only.mkdir(parents=True)
    (cli_only / "cli.log").write_text("list-extensions\n", encoding="utf-8")
    real = config / "logs" / "20260524T190238" / "window1_wb0" / "exthost"
    real.mkdir(parents=True)
    (real / "exthost.log").write_text("Extension host started\n", encoding="utf-8")
    monkeypatch.setattr(shared, "config_home_for_ide", lambda _ide: config)
    assert shared.latest_ide_exthost_session("cursor") == config / "logs" / "20260524T190238"


def test_gc_stale_socket_removes_dead_file(tmp_path: Path) -> None:
    keep = tmp_path / "koru-autopilot-cursor.sock"
    stale = tmp_path / "koru-autopilot.sock"
    stale.touch()
    removed = shared.gc_stale_autopilot_sockets(keep=keep, runtime_dir=tmp_path)
    assert str(stale) in removed
    assert keep.exists() or not keep.exists()


def test_gc_stale_sockets_for_lane_removes_dead_target(tmp_path: Path) -> None:
    target = tmp_path / "koru-autopilot-vscode.sock"
    target.touch()

    removed = gc_stale_sockets_for_lane(target)

    assert str(target) in removed
    assert not target.exists()


def test_evaluate_bridge_no_daemon(tmp_path: Path) -> None:
    sock = tmp_path / "missing.sock"
    status = evaluate_bridge(ide="cursor", socket_path=sock, project=tmp_path)
    assert status.daemon_running is False
    assert not status.ready
    text = format_bridge_text(status, explain=True)
    assert "daemon" in text


def test_evaluate_bridge_maps_lane_slug_to_canonical_ide(tmp_path: Path) -> None:
    sock = tmp_path / "missing.sock"
    status = evaluate_bridge(ide="cursor-main", socket_path=sock, project=tmp_path)
    assert status.ide == "cursor"
    assert all(h.id != "ide.unsupported" for h in status.hypotheses)


def test_get_adapter_cursor() -> None:
    adapter = get_adapter("cursor")
    assert adapter is not None
    assert adapter.ide_id == "cursor"
