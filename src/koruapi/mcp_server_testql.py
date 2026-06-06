"""MCP tool handlers for TestQL GUI/DOM automation bridge."""

from __future__ import annotations

from typing import Any

from koruapi.testql_bridge import (
    testql_list_scenarios,
    testql_run_scenario,
)


def build_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": "koru_testql_list_scenarios",
            "description": (
                "List TestQL scenario files (*.testql.toon.yaml, *.oql) and command catalog "
                "(GUI/DOM via Playwright + native DESKTOP_* via wmctrl/xdotool/wtype/ydotool)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string"},
                    "project_root": {"type": "string"},
                },
            },
        },
        {
            "name": "koru_testql_run_scenario",
            "description": (
                "Run TestQL scenario(s) — GUI_* (Playwright DOM) or DESKTOP_* (native OS). "
                "Default dry_run=true (syntax check only)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_spec": {
                        "type": "string",
                        "description": "Path/glob to .testql.toon.yaml or directory",
                    },
                    "project_dir": {"type": "string"},
                    "project_root": {"type": "string"},
                    "url": {"type": "string", "default": "http://localhost:8101"},
                    "dry_run": {"type": "boolean", "default": True},
                    "timeout": {"type": "integer"},
                },
                "required": ["file_spec"],
            },
        },
    ]


def tool_testql_list_scenarios(arguments: dict[str, Any]) -> dict[str, Any]:
    return testql_list_scenarios(
        project_dir=arguments.get("project_dir"),
        project_root=arguments.get("project_root"),
    )


def tool_testql_run_scenario(arguments: dict[str, Any]) -> dict[str, Any]:
    return testql_run_scenario(
        arguments["file_spec"],
        project_dir=arguments.get("project_dir"),
        project_root=arguments.get("project_root"),
        url=str(arguments.get("url") or "http://localhost:8101"),
        dry_run=bool(arguments.get("dry_run", True)),
        timeout=arguments.get("timeout"),
    )


TOOL_DISPATCH: dict[str, Any] = {
    "koru_testql_list_scenarios": tool_testql_list_scenarios,
    "koru_testql_run_scenario": tool_testql_run_scenario,
}
