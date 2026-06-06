"""MCP tool handlers and schemas for the env2llm live registry bridge."""

from __future__ import annotations

from typing import Any

from koruapi.env2llm_registry import (
    env2llm_get_desktop,
    env2llm_get_registry,
    env2llm_list_commands,
    env2llm_list_uris,
    env2llm_mqtt_status,
    env2llm_refresh_registry,
    env2llm_render_registry,
    env2llm_validate_calibration,
)

_PROJECT_PROPERTIES = {
    "project_dir": {
        "type": "string",
        "description": "Project directory for env2llm registry (default: ENV2LLM_PROJECT_DIR or cwd).",
    },
    "project_root": {
        "type": "string",
        "description": "Alias for project_dir (Koru planfile convention).",
    },
    "project_id": {
        "type": "string",
        "description": "Override example_id / logical project id.",
    },
}


def build_tool_schemas() -> list[dict[str, Any]]:
    """Return tools/list schema entries for env2llm registry MCP tools."""
    return [
        {
            "name": "koru_env2llm_get_registry",
            "description": (
                "Get live env2llm SystemMapIR registry (JSON) for a project. "
                "Requires: pip install 'koru[desktop]' (env2llm>=0.1.5)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_PROJECT_PROPERTIES,
                    "refresh": {
                        "type": "boolean",
                        "default": False,
                        "description": "Regenerate registry before read.",
                    },
                },
            },
        },
        {
            "name": "koru_env2llm_render_registry",
            "description": "Render env2llm registry as doql.less, yaml, json, or markdown.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_PROJECT_PROPERTIES,
                    "format": {
                        "type": "string",
                        "default": "json",
                        "description": "doql.less | yaml | json | markdown",
                    },
                    "refresh": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": "koru_env2llm_refresh_registry",
            "description": (
                "Regenerate and write .nlp2dsl/registry/environment.*; "
                "optional MQTT publish (ENV2LLM_MQTT_ENABLED=1)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_PROJECT_PROPERTIES,
                    "format": {
                        "type": "string",
                        "default": "doql.less",
                    },
                    "probe_desktop": {"type": "boolean"},
                    "publish_mqtt": {"type": "boolean", "default": True},
                },
            },
        },
        {
            "name": "koru_env2llm_get_desktop",
            "description": "Live desktop probe slice (GNOME windows, session, displays).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_PROJECT_PROPERTIES,
                    "refresh": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": "koru_env2llm_list_commands",
            "description": "List command schemas from env2llm registry.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_PROJECT_PROPERTIES,
                    "refresh": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": "koru_env2llm_list_uris",
            "description": (
                "nlp2uri URI index over env2llm registry "
                "(command://, desktop-window://, runtime://, …)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_PROJECT_PROPERTIES,
                    "refresh": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": "koru_env2llm_mqtt_status",
            "description": "MQTT bridge status for env2llm registry fan-out.",
            "inputSchema": {
                "type": "object",
                "properties": dict(_PROJECT_PROPERTIES),
            },
        },
        {
            "name": "koru_env2llm_validate_calibration",
            "description": (
                "Validate IDE calibrations against desktop display geometry. "
                "Detects: top-edge clicks (title bar, not chat), "
                "pointer-display mismatch, stale calibrations."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    **_PROJECT_PROPERTIES,
                    "ide": {
                        "type": "string",
                        "description": "Validate only this IDE (e.g. 'cursor'). Omit for all.",
                    },
                    "refresh": {"type": "boolean", "default": False},
                },
            },
        },
    ]


def _project_kwargs(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_dir": arguments.get("project_dir"),
        "project_root": arguments.get("project_root"),
        "project_id": arguments.get("project_id"),
    }


def tool_env2llm_get_registry(arguments: dict[str, Any]) -> dict[str, Any]:
    return env2llm_get_registry(
        **_project_kwargs(arguments),
        refresh=bool(arguments.get("refresh")),
    )


def tool_env2llm_render_registry(arguments: dict[str, Any]) -> dict[str, Any]:
    return env2llm_render_registry(
        **_project_kwargs(arguments),
        fmt=str(arguments.get("format") or "json"),
        refresh=bool(arguments.get("refresh")),
    )


def tool_env2llm_refresh_registry(arguments: dict[str, Any]) -> dict[str, Any]:
    probe = arguments.get("probe_desktop")
    return env2llm_refresh_registry(
        **_project_kwargs(arguments),
        output_format=str(arguments.get("format") or "doql.less"),
        probe_desktop=probe if probe is not None else None,
        publish_mqtt=bool(arguments.get("publish_mqtt", True)),
    )


def tool_env2llm_get_desktop(arguments: dict[str, Any]) -> dict[str, Any]:
    return env2llm_get_desktop(
        **_project_kwargs(arguments),
        refresh=bool(arguments.get("refresh")),
    )


def tool_env2llm_list_commands(arguments: dict[str, Any]) -> dict[str, Any]:
    return env2llm_list_commands(
        **_project_kwargs(arguments),
        refresh=bool(arguments.get("refresh")),
    )


def tool_env2llm_list_uris(arguments: dict[str, Any]) -> dict[str, Any]:
    return env2llm_list_uris(
        **_project_kwargs(arguments),
        refresh=bool(arguments.get("refresh")),
    )


def tool_env2llm_mqtt_status(arguments: dict[str, Any]) -> dict[str, Any]:
    return env2llm_mqtt_status(**_project_kwargs(arguments))


def tool_env2llm_validate_calibration(arguments: dict[str, Any]) -> dict[str, Any]:
    return env2llm_validate_calibration(
        **_project_kwargs(arguments),
        ide=arguments.get("ide"),
        refresh=bool(arguments.get("refresh")),
    )


TOOL_DISPATCH: dict[str, Any] = {
    "koru_env2llm_get_registry": tool_env2llm_get_registry,
    "koru_env2llm_render_registry": tool_env2llm_render_registry,
    "koru_env2llm_refresh_registry": tool_env2llm_refresh_registry,
    "koru_env2llm_get_desktop": tool_env2llm_get_desktop,
    "koru_env2llm_list_commands": tool_env2llm_list_commands,
    "koru_env2llm_list_uris": tool_env2llm_list_uris,
    "koru_env2llm_mqtt_status": tool_env2llm_mqtt_status,
    "koru_env2llm_validate_calibration": tool_env2llm_validate_calibration,
}
