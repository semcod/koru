"""MCP tool handlers and schemas for the nlp2uri desktop URI bridge."""

from __future__ import annotations

from typing import Any

from koruapi.desktop_uri import (
    desktop_uri_get_getv_var,
    desktop_uri_handle,
    desktop_uri_list_getv,
    desktop_uri_list_system_uris,
    desktop_uri_plan,
    desktop_uri_resolve_getv,
    desktop_uri_resolve_system_map,
)


def build_tool_schemas() -> list[dict[str, Any]]:
    """Return tools/list schema entries for desktop URI MCP tools."""
    return [
        {
            "name": "koru_desktop_uri_plan",
            "description": (
                "Resolve a natural-language desktop command to an abstract URI and OS action plan "
                "via nlp2uri (open app, screenshot, focus window, terminal, settings). "
                "Requires optional dependency: pip install 'koru[desktop]'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Natural-language desktop command (EN or PL).",
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["linux", "darwin", "windows"],
                        "description": "Target OS for compile (default: auto-detect).",
                    },
                    "locale": {
                        "type": "string",
                        "description": "Optional locale hint for NL parsing.",
                    },
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "koru_desktop_uri_handle",
            "description": (
                "Plan and optionally execute a desktop command via nlp2uri. "
                "Dry-run is the default; set dry_run=false to run OS commands. "
                "On Wayland, screen capture can use XDG Portal (koruvision) when available."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Natural-language desktop command (EN or PL).",
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["linux", "darwin", "windows"],
                        "description": "Target OS (default: auto-detect).",
                    },
                    "locale": {
                        "type": "string",
                        "description": "Optional locale hint for NL parsing.",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                        "description": "When true, return compiled argv without executing.",
                    },
                    "use_portal_capture": {
                        "type": "boolean",
                        "description": (
                            "Use XDG Desktop Portal for screen capture on Wayland "
                            "(default: KORU_PORTAL_CAPTURE env or true)."
                        ),
                    },
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "koru_desktop_uri_list_getv_uris",
            "description": "List getv:// URIs for ~/.getv profiles (nlp2uri envmap layer).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "getv_home": {"type": "string", "description": "Override GETV_HOME (default ~/.getv)."},
                },
            },
        },
        {
            "name": "koru_desktop_uri_resolve_getv",
            "description": "Resolve NL prompt to getv:// env var URI (e.g. GROQ_API_KEY).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "getv_home": {"type": "string"},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "koru_desktop_uri_get_getv_var",
            "description": "Read masked metadata for getv://category/profile/VAR.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string", "description": "getv://llm/groq/GROQ_API_KEY"},
                },
                "required": ["uri"],
            },
        },
        {
            "name": "koru_desktop_uri_resolve_system_map",
            "description": (
                "Resolve NL against env2llm SystemMap URIs (command://, runtime://). "
                "Requires doql_path, example_dir, or inline system_map."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "doql_path": {"type": "string"},
                    "example_dir": {"type": "string"},
                    "example_id": {"type": "string"},
                    "system_map": {"type": "object"},
                    "fallback_desktop": {"type": "boolean", "default": True},
                    "platform": {"type": "string", "enum": ["linux", "darwin", "windows"]},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "koru_desktop_uri_list_system_uris",
            "description": "List command:// and runtime:// URIs from env2llm SystemMapIR.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "doql_path": {"type": "string"},
                    "example_dir": {"type": "string"},
                    "example_id": {"type": "string"},
                    "system_map": {"type": "object"},
                },
            },
        },
    ]


def tool_desktop_uri_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    """Resolve NL desktop command to URI + OS action plan (nlp2uri)."""
    return desktop_uri_plan(
        arguments["prompt"],
        platform=arguments.get("platform"),
        locale=arguments.get("locale"),
    )


def tool_desktop_uri_handle(arguments: dict[str, Any]) -> dict[str, Any]:
    """Plan and optionally execute a desktop command (nlp2uri)."""
    return desktop_uri_handle(
        arguments["prompt"],
        platform=arguments.get("platform"),
        locale=arguments.get("locale"),
        dry_run=arguments.get("dry_run", True),
        use_portal_capture=arguments.get("use_portal_capture"),
    )


def tool_desktop_uri_list_getv_uris(arguments: dict[str, Any]) -> dict[str, Any]:
    return desktop_uri_list_getv(getv_home=arguments.get("getv_home"))


def tool_desktop_uri_resolve_getv(arguments: dict[str, Any]) -> dict[str, Any]:
    return desktop_uri_resolve_getv(
        arguments["prompt"],
        getv_home=arguments.get("getv_home"),
    )


def tool_desktop_uri_get_getv_var(arguments: dict[str, Any]) -> dict[str, Any]:
    return desktop_uri_get_getv_var(arguments["uri"])


def tool_desktop_uri_resolve_system_map(arguments: dict[str, Any]) -> dict[str, Any]:
    return desktop_uri_resolve_system_map(
        arguments["prompt"],
        doql_path=arguments.get("doql_path"),
        example_dir=arguments.get("example_dir"),
        example_id=arguments.get("example_id"),
        system_map=arguments.get("system_map"),
        fallback_desktop=arguments.get("fallback_desktop", True),
        platform=arguments.get("platform"),
    )


def tool_desktop_uri_list_system_uris(arguments: dict[str, Any]) -> dict[str, Any]:
    return desktop_uri_list_system_uris(
        doql_path=arguments.get("doql_path"),
        example_dir=arguments.get("example_dir"),
        example_id=arguments.get("example_id"),
        system_map=arguments.get("system_map"),
    )


TOOL_DISPATCH: dict[str, Any] = {
    "koru_desktop_uri_plan": tool_desktop_uri_plan,
    "koru_desktop_uri_handle": tool_desktop_uri_handle,
    "koru_desktop_uri_list_getv_uris": tool_desktop_uri_list_getv_uris,
    "koru_desktop_uri_resolve_getv": tool_desktop_uri_resolve_getv,
    "koru_desktop_uri_get_getv_var": tool_desktop_uri_get_getv_var,
    "koru_desktop_uri_resolve_system_map": tool_desktop_uri_resolve_system_map,
    "koru_desktop_uri_list_system_uris": tool_desktop_uri_list_system_uris,
}
