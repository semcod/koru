"""koru MCP server — compatibility facade and public exports.

Implementation is split across:
  - mcp_server_runtime   — protocol loop + tool dispatch
  - mcp_server_cli       — ``koru mcp-serve`` entry
  - mcp_server_planfile  — tickets, jobs, quality gates
  - mcp_server_ide       — IDE integration tools
  - mcp_server_desktop_uri — nlp2uri bridge
  - mcp_server_env2llm     — env2llm live registry bridge
  - mcp_server_schema    — tools/list schemas
  - mcp_server_dispatch  — JSON-RPC handlers
  - mcp_server_transport — stdio I/O
"""

from __future__ import annotations

from koruapi.mcp_server_cli import mcp_serve_main
from koruapi.mcp_server_desktop_uri import TOOL_DISPATCH as _DESKTOP_URI_TOOL_DISPATCH
from koruapi.mcp_server_ide import (
    tool_ide_command_catalog,
    tool_ide_command_scenario_schema,
    tool_ide_commands,
    tool_ide_drive,
    tool_ide_dsl_recent,
    tool_strategy_prompt,
    tool_validate_ide_command_scenario,
)
from koruapi.mcp_server_planfile import (
    _create_job,
    _gate_commands,
    _jobs,
    _load_jobs,
    _serialize_mcp_ticket,
    _tickets_for_status_filter,
    _update_job,
    tool_job_status,
    tool_list_tickets,
    tool_propose_edits,
    tool_run_quality_gates,
    tool_run_ticket,
)
from koruapi.mcp_server_runtime import (
    PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    TOOL_DISPATCH,
    handle_message,
    jsonrpc_error,
    jsonrpc_response,
    log_stderr,
    run_stdio,
    write_json,
)
from koruapi.mcp_server_schema import TOOLS

_PROTOCOL_VERSION = PROTOCOL_VERSION
_SERVER_NAME = SERVER_NAME
_SERVER_VERSION = SERVER_VERSION
_TOOL_DISPATCH = TOOL_DISPATCH

__all__ = [
    "TOOLS",
    "TOOL_DISPATCH",
    "_PROTOCOL_VERSION",
    "_SERVER_NAME",
    "_SERVER_VERSION",
    "_TOOL_DISPATCH",
    "_create_job",
    "_gate_commands",
    "_jobs",
    "_load_jobs",
    "_serialize_mcp_ticket",
    "_tickets_for_status_filter",
    "_update_job",
    "handle_message",
    "jsonrpc_error",
    "jsonrpc_response",
    "log_stderr",
    "mcp_serve_main",
    "run_stdio",
    "tool_ide_command_catalog",
    "tool_ide_command_scenario_schema",
    "tool_ide_commands",
    "tool_ide_drive",
    "tool_ide_dsl_recent",
    "tool_job_status",
    "tool_list_tickets",
    "tool_propose_edits",
    "tool_run_quality_gates",
    "tool_run_ticket",
    "tool_strategy_prompt",
    "tool_validate_ide_command_scenario",
    "write_json",
]
