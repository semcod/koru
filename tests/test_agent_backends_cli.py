"""Tests for ``koru agent-backends`` CLI."""

from __future__ import annotations

import json

from koru.cli import _agent_backends_main


def test_list_text_prints_ids(capsys) -> None:
    assert _agent_backends_main([]) == 0
    out = capsys.readouterr().out
    assert "vscode_family_plugin_socket" in out


def test_list_json_is_array(capsys) -> None:
    assert _agent_backends_main(["--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    ids = {row["id"] for row in data}
    assert "mcp_stdio_server" in ids


def test_show_one_json(capsys) -> None:
    assert _agent_backends_main(["--format", "json", "mcp_stdio_server"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["id"] == "mcp_stdio_server"
    assert data["mcp_tools_only"] is True


def test_unknown_id_errors(capsys) -> None:
    assert _agent_backends_main(["nope"]) == 2
    assert "unknown" in capsys.readouterr().err
