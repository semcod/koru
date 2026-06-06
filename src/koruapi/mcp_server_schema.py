"""Schema definitions for the Koru MCP server tools."""

from __future__ import annotations

from typing import Any

from koruapi.mcp_server_desktop_uri import build_tool_schemas as _build_desktop_uri_tool_schemas
from koruapi.mcp_server_env2llm import build_tool_schemas as _build_env2llm_tool_schemas
from koruapi.mcp_server_nlp2oql import build_tool_schemas as _build_nlp2oql_tool_schemas
from koruapi.mcp_server_testql import build_tool_schemas as _build_testql_tool_schemas
from koruapi.mcp_server_ide import build_tool_schemas as _build_ide_tool_schemas
from koruapi.mcp_server_planfile import build_tool_schemas as _build_planfile_tool_schemas

PROJECT_ROOT_DESCRIPTION = "Absolute path to project root on disk."


def build_tools(project_root_description: str = PROJECT_ROOT_DESCRIPTION) -> list[dict[str, Any]]:
    """Return MCP tools/list schema payload."""
    return [
        *_build_planfile_tool_schemas(project_root_description=project_root_description),
        *_build_ide_tool_schemas(project_root_description=project_root_description),
        *_build_desktop_uri_tool_schemas(),
        *_build_env2llm_tool_schemas(),
        *_build_testql_tool_schemas(),
        *_build_nlp2oql_tool_schemas(),
    ]


TOOLS = build_tools()
