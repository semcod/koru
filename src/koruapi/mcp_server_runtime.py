"""MCP stdio runtime: protocol constants, tool dispatch, and message loop."""

from __future__ import annotations

from typing import Any

from koruapi.mcp_server_desktop_uri import TOOL_DISPATCH as _DESKTOP_URI_TOOL_DISPATCH
from koruapi.mcp_server_env2llm import TOOL_DISPATCH as _ENV2LLM_TOOL_DISPATCH
from koruapi.mcp_server_nlp2oql import TOOL_DISPATCH as _NLP2OQL_TOOL_DISPATCH
from koruapi.mcp_server_testql import TOOL_DISPATCH as _TESTQL_TOOL_DISPATCH
from koruapi.mcp_server_dispatch import build_method_handlers
from koruapi.mcp_server_dispatch import handle_message as _dispatch_handle_message
from koruapi.mcp_server_dispatch import jsonrpc_error as _dispatch_jsonrpc_error
from koruapi.mcp_server_dispatch import jsonrpc_response as _dispatch_jsonrpc_response
from koruapi.mcp_server_ide import TOOL_DISPATCH as _IDE_TOOL_DISPATCH
from koruapi.mcp_server_planfile import TOOL_DISPATCH as _PLANFILE_TOOL_DISPATCH
from koruapi.mcp_server_schema import TOOLS
from koruapi.mcp_server_transport import log_stderr as _transport_log_stderr
from koruapi.mcp_server_transport import run_stdio_loop
from koruapi.mcp_server_transport import write_json as _transport_write_json

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "koru"
SERVER_VERSION = "0.2.1"

TOOL_DISPATCH: dict[str, Any] = {
    **_PLANFILE_TOOL_DISPATCH,
    **_IDE_TOOL_DISPATCH,
    **_DESKTOP_URI_TOOL_DISPATCH,
    **_ENV2LLM_TOOL_DISPATCH,
    **_TESTQL_TOOL_DISPATCH,
    **_NLP2OQL_TOOL_DISPATCH,
}

_NOTIFICATION_METHODS = frozenset(
    {
        "notifications/initialized",
        "notifications/cancelled",
    }
)

_METHOD_HANDLERS: dict[str, Any] = build_method_handlers(
    protocol_version=PROTOCOL_VERSION,
    server_name=SERVER_NAME,
    server_version=SERVER_VERSION,
    tools=TOOLS,
    tool_dispatch=TOOL_DISPATCH,
)


def handle_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Process one JSON-RPC message and return the response (or None for notifications)."""
    return _dispatch_handle_message(
        msg,
        method_handlers=_METHOD_HANDLERS,
        notification_methods=_NOTIFICATION_METHODS,
    )


def run_stdio() -> int:
    """Main loop: read JSON-RPC from stdin, write responses to stdout."""
    return run_stdio_loop(
        handle_message=handle_message,
        jsonrpc_error=jsonrpc_error,
        logger=log_stderr,
        writer=write_json,
    )


def jsonrpc_response(req_id: Any, result: Any) -> dict[str, Any]:
    return _dispatch_jsonrpc_response(req_id, result)


def jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    return _dispatch_jsonrpc_error(req_id, code, message, data)


def write_json(payload: dict[str, Any]) -> None:
    _transport_write_json(payload)


def log_stderr(msg: str) -> None:
    _transport_log_stderr(msg)
