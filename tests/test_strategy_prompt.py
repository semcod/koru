"""Tests for koruide.strategy_prompt and its REST/MCP surfaces."""

from __future__ import annotations

import json

import pytest

from koru import mcp_server
from koruide.command_catalog import supported_catalog_ides
from koruide.strategy_prompt import (
    STRATEGY_PROMPT_SCHEMA,
    STRATEGY_PROMPT_VERSION,
    build_strategy_prompt,
    format_strategy_prompt_text,
)


def test_build_strategy_prompt_default_returns_all_supported_ides() -> None:
    payload = build_strategy_prompt()
    assert payload["schema"] == STRATEGY_PROMPT_SCHEMA
    assert payload["version"] == STRATEGY_PROMPT_VERSION
    assert payload["ide"] == "all"
    assert set(payload["supported_ides"]) == set(supported_catalog_ides())
    assert "command_catalog" in payload
    assert "scenario_schema" in payload
    assert "policy" in payload
    assert "text" in payload
    assert "Koru IDE strategy prompt" in payload["text"]


def test_build_strategy_prompt_specific_ide_keeps_only_that_ide() -> None:
    payload = build_strategy_prompt("cursor", for_llm=True)
    assert payload["ide"] == "cursor"
    ides = payload["command_catalog"]["ides"]
    assert set(ides.keys()) == {"cursor"}
    assert "categories" in ides["cursor"]


def test_build_strategy_prompt_full_catalog_when_for_llm_false() -> None:
    payload = build_strategy_prompt("cursor", for_llm=False)
    cursor_block = payload["command_catalog"]["ides"]["cursor"]
    assert "commands" in cursor_block
    assert isinstance(cursor_block["commands"], list)
    assert cursor_block["commands"], "cursor static catalog must not be empty"


def test_build_strategy_prompt_include_text_false_omits_text() -> None:
    payload = build_strategy_prompt("cursor", include_text=False)
    assert "text" not in payload


def test_build_strategy_prompt_unknown_ide_raises() -> None:
    with pytest.raises(ValueError):
        build_strategy_prompt("notepad")


def test_format_strategy_prompt_text_is_stable_markdown() -> None:
    payload = build_strategy_prompt("cursor")
    text = format_strategy_prompt_text(payload)
    assert "## Policy" in text
    assert "## Command catalog" in text
    assert "## Output JSON Schema" in text
    assert "koru.ide_command_scenario.v1" in text


def test_mcp_tool_strategy_prompt_returns_payload() -> None:
    response = mcp_server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "koru_strategy_prompt",
                "arguments": {"ide": "cursor"},
            },
        },
    )
    assert response is not None
    result = response["result"]
    assert result.get("isError") is not True
    payload_text = result["content"][0]["text"]
    payload = json.loads(payload_text)
    assert payload["ok"] is True
    assert payload["prompt"]["ide"] == "cursor"
    assert "command_catalog" in payload["prompt"]


def test_mcp_tool_strategy_prompt_unknown_ide_returns_error() -> None:
    response = mcp_server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "koru_strategy_prompt",
                "arguments": {"ide": "notepad"},
            },
        },
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is False
    assert "unknown IDE" in payload["error"]
