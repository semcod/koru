"""JSON-RPC dispatch helpers for the Koru MCP server."""

from __future__ import annotations

import json
import traceback
from typing import Any, Callable


def jsonrpc_response(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def handle_initialize(
    _params: dict[str, Any],
    *,
    protocol_version: str,
    server_name: str,
    server_version: str,
) -> dict[str, Any]:
    return {
        "protocolVersion": protocol_version,
        "capabilities": {
            "tools": {},
        },
        "serverInfo": {
            "name": server_name,
            "version": server_version,
        },
    }


def handle_tools_list(_params: dict[str, Any], *, tools: list[dict[str, Any]]) -> dict[str, Any]:
    return {"tools": tools}


def handle_tools_call(
    params: dict[str, Any],
    *,
    tool_dispatch: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
) -> dict[str, Any]:
    tool_name = params.get("name", "")
    arguments = params.get("arguments") or {}

    handler = tool_dispatch.get(tool_name)
    if handler is None:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
            "isError": True,
        }

    try:
        result = handler(arguments)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, sort_keys=True, default=str),
                },
            ],
        }
    except Exception as exc:
        tb = traceback.format_exc()
        return {
            "content": [{"type": "text", "text": f"Error in {tool_name}: {exc}\n{tb}"}],
            "isError": True,
        }


def build_method_handlers(
    *,
    protocol_version: str,
    server_name: str,
    server_version: str,
    tools: list[dict[str, Any]],
    tool_dispatch: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    return {
        "initialize": lambda params: handle_initialize(
            params,
            protocol_version=protocol_version,
            server_name=server_name,
            server_version=server_version,
        ),
        "tools/list": lambda params: handle_tools_list(params, tools=tools),
        "tools/call": lambda params: handle_tools_call(params, tool_dispatch=tool_dispatch),
    }


def handle_message(
    msg: dict[str, Any],
    *,
    method_handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
    notification_methods: set[str] | frozenset[str],
) -> dict[str, Any] | None:
    """Process one JSON-RPC message and return response, or None for notifications."""
    method = msg.get("method", "")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    if req_id is None or method in notification_methods:
        return None

    handler = method_handlers.get(method)
    if handler is None:
        return jsonrpc_error(req_id, -32601, f"Method not found: {method}")

    try:
        result = handler(params)
        return jsonrpc_response(req_id, result)
    except Exception as exc:
        return jsonrpc_error(req_id, -32603, str(exc))
