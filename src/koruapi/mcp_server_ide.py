"""MCP tool handlers and schemas for Koru IDE integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_tool_schemas(*, project_root_description: str) -> list[dict[str, Any]]:
    """Return tools/list schema entries for IDE MCP tools."""
    return [
        {
            "name": "koru_ide_command_catalog",
            "description": (
                "Return the normalized IDE command/action catalog for LLM planning. "
                "The catalog is candidate-only; Koru verifies live commands before execution."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ide": {
                        "type": "string",
                        "description": "IDE id or all.",
                        "default": "all",
                    },
                    "for_llm": {
                        "type": "boolean",
                        "default": True,
                        "description": "Return compact LLM-oriented catalog.",
                    },
                },
            },
        },
        {
            "name": "koru_ide_command_scenario_schema",
            "description": "Return JSON Schema for Koru IDE command scenarios.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "koru_strategy_prompt",
            "description": (
                "Return the LLM strategy briefing (catalog + scenario schema + policy) "
                "as a ready-to-paste prompt for IDE control planning."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ide": {
                        "type": "string",
                        "description": "IDE id or 'all'.",
                        "default": "all",
                    },
                    "for_llm": {
                        "type": "boolean",
                        "default": True,
                        "description": "Compact category-only catalog (recommended).",
                    },
                    "include_text": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include rendered Markdown 'text' field.",
                    },
                },
            },
        },
        {
            "name": "koru_validate_ide_command_scenario",
            "description": (
                "Validate an LLM-authored IDE command scenario against Koru's command catalog "
                "and risk policy."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "object",
                        "description": "Scenario object matching koru.ide_command_scenario.v1.",
                        "additionalProperties": True,
                    },
                },
                "required": ["scenario"],
            },
        },
        {
            "name": "koru_ide_commands",
            "description": (
                "Return the runtime IDE command catalog and per-command telemetry "
                "for a connected Koru autopilot plugin (focus/paste/submit candidates)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": project_root_description,
                    },
                    "ide": {
                        "type": "string",
                        "description": "IDE id (cursor, vscode, windsurf, vscodium, antigravity).",
                    },
                    "capability": {
                        "type": "string",
                        "description": "Optional capability filter (focus_open, paste, submit, ...).",
                    },
                },
                "required": ["project_root"],
            },
        },
        {
            "name": "koru_ide_list_uris",
            "description": (
                "Export ide:// / ide-chat:// URI index from live autopilot status "
                "(koru autopilot status + nlp2uri systemmap)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": project_root_description,
                    },
                    "ide": {
                        "type": "string",
                        "description": "IDE lane for socket selection (default: auto).",
                    },
                },
            },
        },
        {
            "name": "koru_ide_control_plan",
            "description": (
                "Resolve natural language to a Koru IDE control plan (ide-chat://, "
                "koru-control://) with koru.control.v1 replay metadata."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "NL prompt, e.g. 'send this to Cursor chat'.",
                    },
                    "platform": {
                        "type": "string",
                        "description": "Host platform hint (linux, darwin, windows).",
                    },
                    "locale": {"type": "string"},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "koru_ide_control_execute",
            "description": (
                "Plan and optionally execute IDE control via nlp2uri koruide driver. "
                "Defaults to dry_run=true."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "text": {
                        "type": "string",
                        "description": "Optional prompt body override for drive operations.",
                    },
                    "platform": {"type": "string"},
                    "locale": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": True},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "koru_ide_drive",
            "description": (
                "Send a prompt to the IDE chat via the koruide daemon drive/chat.send path."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": project_root_description,
                    },
                    "text": {"type": "string", "description": "Prompt text to paste into IDE chat."},
                    "ide": {
                        "type": "string",
                        "description": "Target IDE (default: auto).",
                    },
                    "submit": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to submit after paste.",
                    },
                    "strategy_hint": {
                        "type": "string",
                        "description": "Optional picker hint (e.g. llm).",
                    },
                },
                "required": ["project_root", "text"],
            },
        },
        {
            "name": "koru_ide_dsl_recent",
            "description": "Return recent Koru Drive DSL trace lines from the autopilot daemon.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": project_root_description,
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20,
                        "description": "Maximum number of DSL lines to return.",
                    },
                },
                "required": ["project_root"],
            },
        },
    ]


def tool_ide_command_catalog(arguments: dict[str, Any]) -> dict[str, Any]:
    from koruide.command_catalog import build_ide_command_catalog, command_catalog_for_llm

    ide_raw = arguments.get("ide", "all")
    ide = None if ide_raw in (None, "", "all") else str(ide_raw)
    for_llm = bool(arguments.get("for_llm", True))
    catalog = command_catalog_for_llm(ide) if for_llm else build_ide_command_catalog(ide)
    return {"catalog": catalog}


def tool_ide_command_scenario_schema(_arguments: dict[str, Any]) -> dict[str, Any]:
    from koruide.command_scenario import ide_command_scenario_schema

    return {"schema": ide_command_scenario_schema()}


def tool_strategy_prompt(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return Koru's LLM-ready IDE strategy prompt."""
    from koruide.strategy_prompt import build_strategy_prompt

    ide_raw = arguments.get("ide", "all")
    ide = None if ide_raw in (None, "", "all") else str(ide_raw)
    for_llm = bool(arguments.get("for_llm", True))
    include_text = bool(arguments.get("include_text", True))
    try:
        payload = build_strategy_prompt(ide, for_llm=for_llm, include_text=include_text)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "prompt": payload}


def tool_ide_commands(arguments: dict[str, Any]) -> dict[str, Any]:
    """Expose stored runtime command catalog + telemetry for IDE LLM introspection."""
    from koruide.command_catalog import build_ide_command_catalog
    from koruide.command_catalog_store import CommandCatalogStore
    from koruide.command_telemetry import CommandTelemetry

    project = Path(arguments["project_root"]).resolve()
    ide = arguments.get("ide")
    capability = arguments.get("capability")
    store = CommandCatalogStore(project)
    telemetry = CommandTelemetry(project)
    static = build_ide_command_catalog(ide if isinstance(ide, str) else None)
    if isinstance(ide, str):
        entry = store.get(ide)
        rows = telemetry.rows_for(
            ide,
            capability=capability if isinstance(capability, str) else None,
        )
        return {
            "ide": ide,
            "capability": capability,
            "static_catalog": static,
            "runtime_catalog": {ide: entry} if entry else {},
            "telemetry": rows,
        }
    return {
        "static_catalog": static,
        "runtime_catalog": {ide_id: store.get(ide_id) for ide_id in store.all_ides()},
        "telemetry_ides": store.all_ides(),
    }


def tool_ide_list_uris(arguments: dict[str, Any]) -> dict[str, Any]:
    from koruide.client import AutopilotClient
    from koruide.socket import default_socket_path

    from koruapi.desktop_uri import desktop_uri_list_koru_ide_uris, nlp2uri_available, nlp2uri_missing_message

    if not nlp2uri_available():
        return {"ok": False, "error": nlp2uri_missing_message()}
    ide = str(arguments.get("ide", "auto"))
    client = AutopilotClient(socket_path=default_socket_path(), timeout=15.0)
    if not client.is_running():
        return {"ok": False, "error": "koruide daemon is not running"}
    status = client.status()
    if not isinstance(status, dict):
        return {"ok": False, "error": "unexpected status payload"}
    payload = desktop_uri_list_koru_ide_uris(
        status,
        socket_path=str(client.socket_path),
    )
    payload["ide"] = ide
    return payload


def tool_ide_control_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    from koruapi.desktop_uri import desktop_uri_control_plan, nlp2uri_available, nlp2uri_missing_message

    if not nlp2uri_available():
        return {"ok": False, "error": nlp2uri_missing_message()}
    return desktop_uri_control_plan(
        str(arguments.get("prompt", "")),
        platform=arguments.get("platform"),
        locale=arguments.get("locale"),
    )


def tool_ide_control_execute(arguments: dict[str, Any]) -> dict[str, Any]:
    from koruapi.desktop_uri import desktop_uri_control_execute, nlp2uri_available, nlp2uri_missing_message

    if not nlp2uri_available():
        return {"ok": False, "error": nlp2uri_missing_message()}
    return desktop_uri_control_execute(
        str(arguments.get("prompt", "")),
        platform=arguments.get("platform"),
        locale=arguments.get("locale"),
        dry_run=bool(arguments.get("dry_run", True)),
        text=arguments.get("text"),
    )


def tool_ide_drive(arguments: dict[str, Any]) -> dict[str, Any]:
    """Drive IDE chat through koruide daemon."""
    from koruide.client import AutopilotClient
    from koruide.socket import default_socket_path

    text = str(arguments.get("text", ""))
    if not text.strip():
        return {"ok": False, "error": "text is required"}
    ide = str(arguments.get("ide", "auto"))
    submit = bool(arguments.get("submit", True))
    strategy_hint = arguments.get("strategy_hint")
    client = AutopilotClient(socket_path=default_socket_path(), timeout=45.0)
    if not client.is_running():
        return {"ok": False, "error": "koruide daemon is not running"}
    reply = client.drive(
        text,
        submit=submit,
        ide=ide,
        require_plugin=False,
        strategy_hint=strategy_hint if isinstance(strategy_hint, str) else None,
    )
    return {"ok": bool(reply.get("ok", True)), "reply": reply}


def tool_ide_dsl_recent(arguments: dict[str, Any]) -> dict[str, Any]:
    """Read persisted recent Drive DSL lines."""
    project = Path(arguments["project_root"]).resolve()
    limit = int(arguments.get("limit", 20))
    path = project / ".planfile" / ".koru" / "dsl_recent.json"
    if not path.is_file():
        return {"lines": [], "source": str(path), "count": 0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"lines": [], "error": str(exc), "source": str(path), "count": 0}
    lines = data.get("lines") if isinstance(data, dict) else []
    if not isinstance(lines, list):
        lines = []
    trimmed = [line for line in lines if isinstance(line, str)][-limit:]
    return {"lines": trimmed, "source": str(path), "count": len(trimmed)}


def tool_validate_ide_command_scenario(arguments: dict[str, Any]) -> dict[str, Any]:
    from koruide.command_scenario import validate_ide_command_scenario

    scenario = arguments.get("scenario")
    if not isinstance(scenario, dict):
        return {
            "ok": False,
            "validation": {
                "ok": False,
                "errors": ["scenario must be an object"],
                "warnings": [],
                "normalized": {},
            },
        }
    validation = validate_ide_command_scenario(scenario)
    return {"ok": validation.ok, "validation": validation.to_dict()}


TOOL_DISPATCH: dict[str, Any] = {
    "koru_ide_list_uris": tool_ide_list_uris,
    "koru_ide_control_plan": tool_ide_control_plan,
    "koru_ide_control_execute": tool_ide_control_execute,
    "koru_ide_command_catalog": tool_ide_command_catalog,
    "koru_ide_command_scenario_schema": tool_ide_command_scenario_schema,
    "koru_strategy_prompt": tool_strategy_prompt,
    "koru_validate_ide_command_scenario": tool_validate_ide_command_scenario,
    "koru_ide_commands": tool_ide_commands,
    "koru_ide_drive": tool_ide_drive,
    "koru_ide_dsl_recent": tool_ide_dsl_recent,
}
