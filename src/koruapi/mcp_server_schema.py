"""Schema definitions for the Koru MCP server tools."""

from __future__ import annotations

from typing import Any

PROJECT_ROOT_DESCRIPTION = "Absolute path to project root on disk."


def build_tools(project_root_description: str = PROJECT_ROOT_DESCRIPTION) -> list[dict[str, Any]]:
    """Return MCP tools/list schema payload."""
    return [
        {
            "name": "koru_list_tickets",
            "description": (
                "List open koru tickets for a given project (planfile queue). "
                "Returns ticket id, title, status, priority, executor kind, and associated files."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": project_root_description,
                    },
                    "queue_name": {
                        "type": "string",
                        "description": "Optional queue name if multiple queues exist.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["open", "in_progress", "done", "all"],
                        "default": "open",
                        "description": "Filter tickets by status.",
                    },
                },
                "required": ["project_root"],
            },
        },
        {
            "name": "koru_run_ticket",
            "description": (
                "Run koru autopilot/planfile pipeline for a single ticket. "
                "Executes a closed-loop: scan -> plan -> apply changes -> run tests -> quality gates."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": project_root_description,
                    },
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID from koru queue.",
                    },
                    "queue_name": {
                        "type": "string",
                        "description": "Optional planfile execution queue (koru --queue-name).",
                    },
                    "actor": {
                        "type": "string",
                        "description": "Optional actor for ticket claim metadata (koru --actor).",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["dry", "apply"],
                        "default": "apply",
                        "description": "Dry-run only or apply changes to the working tree.",
                    },
                    "max_steps": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Optional safety limit on number of steps/iterations.",
                    },
                    "oom_kill_threshold_mb": {
                        "type": "integer",
                        "minimum": 100,
                        "description": (
                            "Memory limit in MB before killing subprocess (default: 4096). "
                            "Set to 0 to disable."
                        ),
                    },
                    "oom_monitor_interval_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Polling interval for memory stats in seconds (default: 5).",
                    },
                    "oom_action": {
                        "type": "string",
                        "enum": ["kill", "warn", "continue"],
                        "default": "kill",
                        "description": (
                            "Action when OOM is detected: kill subprocess, warn only, or continue."
                        ),
                    },
                },
                "required": ["project_root", "ticket_id"],
            },
        },
        {
            "name": "koru_job_status",
            "description": "Check status of a long-running koru job.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID returned by koru_run_ticket.",
                    },
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "koru_run_quality_gates",
            "description": (
                "Run koru quality gates (regix, redup, vallm, sumr, etc.) for a project. "
                "Returns per-gate pass/fail status and issue details."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": project_root_description,
                    },
                    "gates": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["regix", "redup", "vallm", "sumr", "testql", "security"],
                        },
                        "description": "Subset of gates to run; if omitted, run all configured.",
                    },
                    "fail_fast": {
                        "type": "boolean",
                        "default": True,
                        "description": "Stop on first failing gate when true.",
                    },
                    "oom_kill_threshold_mb": {
                        "type": "integer",
                        "minimum": 100,
                        "description": (
                            "Memory limit in MB before killing subprocess (default: 2048). "
                            "Set to 0 to disable."
                        ),
                    },
                    "oom_monitor_interval_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Polling interval for memory stats in seconds (default: 5).",
                    },
                    "oom_action": {
                        "type": "string",
                        "enum": ["kill", "warn", "continue"],
                        "default": "kill",
                        "description": (
                            "Action when OOM is detected: kill subprocess, warn only, or continue."
                        ),
                    },
                },
                "required": ["project_root"],
            },
        },
        {
            "name": "koru_propose_edits",
            "description": (
                "Propose code edits for a given ticket as file edits (no direct writes). "
                "Returns edit operations that the IDE can apply locally."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": project_root_description,
                    },
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID from koru queue for which to propose edits.",
                    },
                    "files_scope": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional whitelist of files to modify (relative paths).",
                    },
                    "max_edits": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Optional safety cap on number of edits.",
                    },
                },
                "required": ["project_root", "ticket_id"],
            },
        },
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


TOOLS = build_tools()
