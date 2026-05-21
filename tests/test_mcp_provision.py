from __future__ import annotations

import json
from pathlib import Path

from koru import mcp_provision


def test_detect_ides_uses_runtime_bridge(monkeypatch) -> None:
    monkeypatch.setattr(
        mcp_provision,
        "detect_running_ides",
        lambda: [{"id": "cursor"}, {"id": "vscode"}],
    )

    out = mcp_provision.detect_ides()

    assert out == ["cursor", "vscode"]


def test_provision_cursor_dry_run_does_not_write(tmp_path: Path) -> None:
    result = mcp_provision.provision_cursor(tmp_path, dry_run=True)

    assert result["ide"] == "cursor"
    assert result["action"] == "added"
    assert result["dry_run"] is True
    assert not (tmp_path / ".cursor" / "mcp.json").exists()


def test_provision_cursor_writes_file_and_then_is_idempotent(tmp_path: Path) -> None:
    first = mcp_provision.provision_cursor(tmp_path, dry_run=False)
    assert first["action"] == "added"

    cfg_path = tmp_path / ".cursor" / "mcp.json"
    assert cfg_path.exists()

    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    cmd = payload["mcpServers"]["koru"]["command"]
    assert cmd == "koru" or Path(cmd).name == "koru"

    second = mcp_provision.provision_cursor(tmp_path, dry_run=False)
    assert second["action"] == "already_configured"


def test_provision_zed_writes_context_servers(tmp_path: Path) -> None:
    result = mcp_provision.provision_zed(tmp_path, dry_run=False)

    assert result["ide"] == "zed"
    assert result["action"] == "added"
    cfg_path = tmp_path / ".zed" / "settings.json"
    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert payload["context_servers"]["koru"]["args"] == ["mcp-serve"]


def test_provision_vscodium_uses_vscode_workspace_mcp_file(tmp_path: Path) -> None:
    result = mcp_provision.provision_vscodium(tmp_path, dry_run=False)

    assert result["ide"] == "vscodium"
    assert result["action"] == "added"
    assert (tmp_path / ".vscode" / "mcp.json").exists()


def test_provision_upgrades_bare_koru_command_to_absolute(tmp_path: Path, monkeypatch) -> None:
    cfg_path = tmp_path / ".cursor" / "mcp.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    fake_koru = tmp_path / "bin-koru-fake"
    fake_koru.write_text("#!/bin/sh\necho\n", encoding="utf-8")
    fake_koru.chmod(0o755)

    monkeypatch.setattr(
        mcp_provision.shutil, "which", lambda _cmd: str(fake_koru) if _cmd == "koru" else None
    )

    cfg_path.write_text(
        json.dumps({"mcpServers": {"koru": {"command": "koru", "args": ["mcp-serve"]}}}),
        encoding="utf-8",
    )

    result = mcp_provision.provision_cursor(tmp_path, dry_run=False)
    assert result["action"] == "updated"

    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert payload["mcpServers"]["koru"]["command"] == str(fake_koru)


def test_remove_from_config_removes_koru_entry(tmp_path: Path) -> None:
    cfg_path = tmp_path / ".cursor" / "mcp.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "koru": {"command": "koru", "args": ["mcp-serve"]},
                    "other": {"command": "python3", "args": ["-m", "x"]},
                },
            },
        ),
        encoding="utf-8",
    )

    result = mcp_provision.remove_from_config(cfg_path, dry_run=False)
    assert result["action"] == "removed"

    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "koru" not in payload["mcpServers"]
    assert "other" in payload["mcpServers"]


def test_remove_from_config_removes_zed_context_server(tmp_path: Path) -> None:
    cfg_path = tmp_path / ".zed" / "settings.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        json.dumps(
            {
                "context_servers": {
                    "koru": {"command": "koru", "args": ["mcp-serve"]},
                    "other": {"command": "python3", "args": ["-m", "x"]},
                },
            },
        ),
        encoding="utf-8",
    )

    result = mcp_provision.remove_from_config(
        cfg_path,
        dry_run=False,
        server_key="context_servers",
    )
    assert result["action"] == "removed"

    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "koru" not in payload["context_servers"]
    assert "other" in payload["context_servers"]


def test_init_ide_main_json_output_for_cursor_dry_run(capsys, tmp_path: Path) -> None:
    code = mcp_provision.init_ide_main(
        [
            "--ide",
            "cursor",
            "--project",
            str(tmp_path),
            "--dry-run",
            "--format",
            "json",
        ],
    )

    assert code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert isinstance(payload, list)
    assert payload[0]["ide"] == "cursor"
    assert payload[0]["action"] in {"added", "already_configured", "updated"}


def test_init_ide_main_json_output_for_zed_dry_run(capsys, tmp_path: Path) -> None:
    code = mcp_provision.init_ide_main(
        [
            "--ide",
            "zed-editor",
            "--project",
            str(tmp_path),
            "--dry-run",
            "--format",
            "json",
        ],
    )

    assert code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload[0]["ide"] == "zed"
    assert payload[0]["action"] == "added"


def test_ensure_koru_mcp_not_disabled_clears_disabled_and_keeps_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = tmp_path / ".cursor" / "mcp.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    fake_koru = tmp_path / "bin-koru"
    fake_koru.write_text("#!/bin/sh\necho\n", encoding="utf-8")
    fake_koru.chmod(0o755)
    monkeypatch.setattr(
        mcp_provision.shutil, "which", lambda _c: str(fake_koru) if _c == "koru" else None
    )

    cfg.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "koru": {
                        "disabled": True,
                        "command": "koru",
                        "args": ["mcp-serve"],
                    },
                },
            },
        ),
        encoding="utf-8",
    )

    rows = mcp_provision.ensure_koru_mcp_not_disabled(tmp_path)
    assert len(rows) == 1
    assert rows[0]["action"] == "mcp_refreshed"

    payload = json.loads(cfg.read_text(encoding="utf-8"))
    koru = payload["mcpServers"]["koru"]
    assert "disabled" not in koru
    assert koru["command"] == str(fake_koru)


def test_ensure_koru_mcp_not_disabled_includes_global_windsurf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gpath = tmp_path / "windsurf-global-mcp.json"
    monkeypatch.setattr(mcp_provision, "_windsurf_global_config", lambda: gpath)
    fake_koru = tmp_path / "bin-koru"
    fake_koru.write_text("#!/bin/sh\necho\n", encoding="utf-8")
    fake_koru.chmod(0o755)
    monkeypatch.setattr(
        mcp_provision.shutil, "which", lambda _c: str(fake_koru) if _c == "koru" else None
    )

    gpath.write_text(
        json.dumps(
            {"mcpServers": {"koru": {"disabled": True, "command": "koru", "args": ["mcp-serve"]}}},
        ),
        encoding="utf-8",
    )

    rows = mcp_provision.ensure_koru_mcp_not_disabled(tmp_path)
    assert any(r["path"] == str(gpath) for r in rows)
    payload = json.loads(gpath.read_text(encoding="utf-8"))
    assert "disabled" not in payload["mcpServers"]["koru"]


def test_ensure_koru_mcp_not_disabled_handles_zed_context_servers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = tmp_path / ".zed" / "settings.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    fake_koru = tmp_path / "bin-koru"
    fake_koru.write_text("#!/bin/sh\necho\n", encoding="utf-8")
    fake_koru.chmod(0o755)
    monkeypatch.setattr(
        mcp_provision.shutil,
        "which",
        lambda _c: str(fake_koru) if _c == "koru" else None,
    )

    cfg.write_text(
        json.dumps(
            {
                "context_servers": {
                    "koru": {
                        "disabled": True,
                        "command": "koru",
                        "args": ["mcp-serve"],
                    },
                },
            },
        ),
        encoding="utf-8",
    )

    rows = mcp_provision.ensure_koru_mcp_not_disabled(tmp_path)
    assert len(rows) == 1
    payload = json.loads(cfg.read_text(encoding="utf-8"))
    koru = payload["context_servers"]["koru"]
    assert "disabled" not in koru
    assert koru["command"] == str(fake_koru)
