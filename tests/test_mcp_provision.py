from __future__ import annotations

import json
from pathlib import Path

from koru import mcp_provision


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
    assert payload["mcpServers"]["koru"]["command"] == "koru"
    assert payload["mcpServers"]["koru"]["args"] == ["mcp-serve"]

    second = mcp_provision.provision_cursor(tmp_path, dry_run=False)
    assert second["action"] == "already_configured"


def test_remove_from_config_removes_koru_entry(tmp_path: Path) -> None:
    cfg_path = tmp_path / ".cursor" / "mcp.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "koru": {"command": "koru", "args": ["mcp-serve"]},
                    "other": {"command": "python3", "args": ["-m", "x"]},
                }
            }
        ),
        encoding="utf-8",
    )

    result = mcp_provision.remove_from_config(cfg_path, dry_run=False)
    assert result["action"] == "removed"

    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "koru" not in payload["mcpServers"]
    assert "other" in payload["mcpServers"]


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
        ]
    )

    assert code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert isinstance(payload, list)
    assert payload[0]["ide"] == "cursor"
    assert payload[0]["action"] in {"added", "already_configured"}
