"""Tests for koru.autonomy.environment + heal (autodetect + auto-repair)."""

from __future__ import annotations

import json
import socket as _socket
from pathlib import Path
from unittest.mock import patch

from koru.autonomy.environment import (
    KNOWN_IDES,
    SocketHealth,
    probe_environment,
    probe_ide_presence,
    probe_socket_health,
)
from koru.autonomy.heal import (
    heal_environment,
    remove_stale_socket,
    summarise,
)

# --- probe_socket_health ----------------------------------------------------


def test_probe_socket_health_missing_file(tmp_path: Path) -> None:
    h = probe_socket_health(tmp_path / "nonexistent.sock")
    assert h.exists is False
    assert h.listening is False
    assert h.stale is False
    assert h.healthy is False


def test_probe_socket_health_stale_socket(tmp_path: Path) -> None:
    """File exists, but no listener → stale."""
    stale = tmp_path / "stale.sock"
    stale.write_bytes(b"")  # plain file, not a real socket
    h = probe_socket_health(stale)
    assert h.exists is True
    assert h.listening is False
    assert h.stale is True


def test_probe_socket_health_listening_socket(tmp_path: Path) -> None:
    """Real listening Unix socket → healthy."""
    sock_path = tmp_path / "live.sock"
    srv = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(1)
    try:
        h = probe_socket_health(sock_path)
        assert h.exists is True
        assert h.listening is True
        assert h.stale is False
        assert h.healthy is True
    finally:
        srv.close()


# --- probe_ide_presence ------------------------------------------------------


def test_probe_ide_presence_returns_entry_per_known_ide(tmp_path: Path) -> None:
    presences = probe_ide_presence(tmp_path, environ={"PATH": "/nonexistent"})
    found = {p.ide for p in presences}
    for ide in KNOWN_IDES:
        assert ide in found
    # With an empty PATH, nothing is installed
    assert all(not p.installed for p in presences)


def test_probe_ide_presence_detects_installed_binary(tmp_path: Path) -> None:
    """If `cursor` is on PATH, presence.installed must be True."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "cursor").write_text("#!/bin/sh\nexit 0\n")
    (bin_dir / "cursor").chmod(0o755)

    presences = probe_ide_presence(tmp_path, environ={"PATH": str(bin_dir)})
    cursor = next(p for p in presences if p.ide == "cursor")
    assert cursor.installed is True
    assert cursor.binary_path is not None
    assert cursor.binary_path.endswith("/cursor")


def test_probe_ide_presence_detects_koru_in_cursor_mcp(tmp_path: Path) -> None:
    """When project has .cursor/mcp.json with koru entry, mcp_has_koru is True."""
    cfg_dir = tmp_path / ".cursor"
    cfg_dir.mkdir()
    (cfg_dir / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru"}}}),
    )

    presences = probe_ide_presence(tmp_path)
    cursor = next(p for p in presences if p.ide == "cursor")
    assert cursor.mcp_has_koru is True


def test_probe_ide_presence_ignores_disabled_koru(tmp_path: Path) -> None:
    """A disabled koru entry must not count as MCP-enabled."""
    cfg_dir = tmp_path / ".cursor"
    cfg_dir.mkdir()
    (cfg_dir / "mcp.json").write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "disabled": True}}}),
    )

    presences = probe_ide_presence(tmp_path)
    cursor = next(p for p in presences if p.ide == "cursor")
    assert cursor.mcp_has_koru is False


# --- probe_environment ------------------------------------------------------


def test_probe_environment_headless_via_env(tmp_path: Path) -> None:
    report = probe_environment(tmp_path, environ={"KORU_HEADLESS": "1", "PATH": ""})
    assert report.headless is True
    assert report.can_use_plugin_socket is False
    assert any("headless" in n.lower() for n in report.notes)


def test_probe_environment_flags_stale_socket(tmp_path: Path) -> None:
    stale = tmp_path / "stale.sock"
    stale.write_bytes(b"")
    report = probe_environment(
        tmp_path,
        autopilot_socket=stale,
        environ={"PATH": ""},
    )
    assert report.autopilot_socket is not None
    assert report.autopilot_socket.stale is True
    assert any("stale autopilot socket" in issue for issue in report.fixable_issues)


def test_probe_environment_flags_missing_mcp_when_ide_installed(tmp_path: Path) -> None:
    """IDE installed but MCP not configured → fixable issue suggests bootstrap."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "cursor").write_text("#!/bin/sh\nexit 0\n")
    (bin_dir / "cursor").chmod(0o755)

    fake_cfg = tmp_path / "no-mcp.json"
    with (
        patch("koru.mcp_provision._cursor_project_config", return_value=fake_cfg),
        patch("koru.mcp_provision._vscode_project_config", return_value=fake_cfg),
        patch("koru.mcp_provision._windsurf_project_config", return_value=fake_cfg),
        patch("koru.mcp_provision._windsurf_global_config", return_value=fake_cfg),
    ):
        report = probe_environment(tmp_path, environ={"PATH": str(bin_dir)})
    assert "cursor" in report.installed_ides
    assert report.mcp_enabled_ides == []
    assert any("koru:mcp:bootstrap" in issue for issue in report.fixable_issues)


# --- heal: remove_stale_socket ---------------------------------------------


def test_remove_stale_socket_skips_when_not_stale(tmp_path: Path) -> None:
    healthy = SocketHealth(path=tmp_path / "x.sock", exists=True, listening=True, stale=False)
    r = remove_stale_socket(healthy)
    assert r.status == "skipped"


def test_remove_stale_socket_dry_run_does_not_mutate(tmp_path: Path) -> None:
    p = tmp_path / "stale.sock"
    p.write_bytes(b"")
    stale = SocketHealth(path=p, exists=True, listening=False, stale=True)
    r = remove_stale_socket(stale, dry_run=True)
    assert r.status == "dry_run"
    assert p.exists()  # not deleted


def test_remove_stale_socket_fixes_real_stale_socket(tmp_path: Path) -> None:
    p = tmp_path / "stale.sock"
    p.write_bytes(b"")
    stale = SocketHealth(path=p, exists=True, listening=False, stale=True)
    r = remove_stale_socket(stale)
    assert r.status == "fixed"
    assert not p.exists()


def test_remove_stale_socket_idempotent_after_fix(tmp_path: Path) -> None:
    """Calling after the file is already gone returns skipped, not failed."""
    p = tmp_path / "stale.sock"
    stale = SocketHealth(path=p, exists=True, listening=False, stale=True)
    r = remove_stale_socket(stale)
    assert r.status == "skipped"
    assert "already gone" in r.detail


# --- heal: heal_environment integration -------------------------------------


def test_heal_environment_repairs_stale_socket(tmp_path: Path) -> None:
    stale = tmp_path / "stale.sock"
    stale.write_bytes(b"")
    report = probe_environment(
        tmp_path,
        autopilot_socket=stale,
        environ={"PATH": ""},
    )
    results = heal_environment(report)
    assert len(results) == 1
    assert results[0].action == "remove_stale_socket"
    assert results[0].status == "fixed"
    assert not stale.exists()


def test_heal_environment_no_op_on_clean_env(tmp_path: Path) -> None:
    report = probe_environment(tmp_path, environ={"PATH": ""})
    results = heal_environment(report)
    assert results == []


def test_summarise_no_repairs() -> None:
    assert summarise([]) == "self-heal: nothing to fix"


def test_summarise_counts_statuses(tmp_path: Path) -> None:
    p = tmp_path / "stale.sock"
    p.write_bytes(b"")
    stale = SocketHealth(path=p, exists=True, listening=False, stale=True)
    results = [remove_stale_socket(stale), remove_stale_socket(stale)]
    msg = summarise(results)
    assert "fixed=1" in msg
    assert "skipped=1" in msg
