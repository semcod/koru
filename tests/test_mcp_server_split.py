from __future__ import annotations

import io
import json

from koruapi import mcp_server_dispatch, mcp_server_schema, mcp_server_transport


def test_schema_tools_regression_contains_expected_tool_names() -> None:
    tools = mcp_server_schema.TOOLS
    names = {tool["name"] for tool in tools}

    assert {
        "koru_list_tickets",
        "koru_run_ticket",
        "koru_job_status",
        "koru_run_quality_gates",
        "koru_propose_edits",
        "koru_ide_command_catalog",
        "koru_ide_command_scenario_schema",
        "koru_validate_ide_command_scenario",
        "koru_ide_commands",
        "koru_ide_drive",
        "koru_ide_dsl_recent",
        "koru_strategy_prompt",
    }.issubset(names)


def test_dispatch_handle_message_returns_method_not_found() -> None:
    method_handlers = mcp_server_dispatch.build_method_handlers(
        protocol_version="2024-11-05",
        server_name="koru",
        server_version="0.2.1",
        tools=[],
        tool_dispatch={},
    )
    response = mcp_server_dispatch.handle_message(
        {"jsonrpc": "2.0", "id": 5, "method": "unknown/method", "params": {}},
        method_handlers=method_handlers,
        notification_methods=frozenset({"notifications/initialized"}),
    )

    assert response is not None
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]


def test_dispatch_tools_call_formats_handler_error() -> None:
    def _boom(_arguments: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("explode")

    result = mcp_server_dispatch.handle_tools_call(
        {"name": "demo", "arguments": {}},
        tool_dispatch={"demo": _boom},
    )

    assert result["isError"] is True
    assert "Error in demo: explode" in result["content"][0]["text"]


def test_transport_run_stdio_loop_handles_parse_error_and_message_flow() -> None:
    stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}\nnot-json\n')
    stdout = io.StringIO()
    stderr = io.StringIO()

    def _handle_message(msg: dict[str, object]) -> dict[str, object] | None:
        if msg.get("method") == "ping":
            return {"jsonrpc": "2.0", "id": msg.get("id"), "result": {"ok": True}}
        return None

    rc = mcp_server_transport.run_stdio_loop(
        handle_message=_handle_message,
        jsonrpc_error=mcp_server_dispatch.jsonrpc_error,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )

    assert rc == 0
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == 2

    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["result"]["ok"] is True
    assert second["error"]["code"] == -32700
