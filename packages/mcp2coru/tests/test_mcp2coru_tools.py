"""Legacy MCP tool names are aliases, not parallel implementations."""

import importlib

from mcp2koru import tools as canonical_tools


def test_legacy_tool_names_alias_canonical_tools() -> None:
    tools = importlib.import_module("mcp2coru.tools")
    assert tools.coru_run_command is canonical_tools.koru_run_command
    assert tools.coru_run_command_pb is canonical_tools.koru_run_command_pb
    assert tools.coru_run_dsl is canonical_tools.koru_run_dsl
    assert tools.coru_to_dsl is canonical_tools.koru_to_dsl
