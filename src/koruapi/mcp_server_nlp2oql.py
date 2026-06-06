"""MCP tool handlers for nlp2oql browser automation router."""

from __future__ import annotations

from typing import Any

from koruapi.nlp2oql_bridge import nlp2oql_generate, nlp2oql_run


def build_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": "koru_nlp2oql_generate",
            "description": (
                "Generate TestQL OQL from NL using env2llm context. "
                "Use for CI/regression scenarios (testql backend)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "project_dir": {"type": "string"},
                    "project_root": {"type": "string"},
                    "use_llm": {"type": "boolean", "default": False},
                    "validate": {"type": "boolean", "default": True},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "koru_nlp2oql_run",
            "description": (
                "Route NL browser task to testql, nlp2cmd, or curllm. "
                "Login/form/captcha → curllm; multi-step/canvas → nlp2cmd; "
                "tests/API/desktop → testql. Default plan-only unless execute=true."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "project_dir": {"type": "string"},
                    "project_root": {"type": "string"},
                    "backend": {
                        "type": "string",
                        "enum": ["testql", "nlp2cmd", "curllm"],
                    },
                    "execute": {"type": "boolean", "default": False},
                    "url": {"type": "string"},
                    "captcha_solver": {"type": "boolean", "default": False},
                    "visual_mode": {"type": "boolean", "default": False},
                },
                "required": ["prompt"],
            },
        },
    ]


def tool_nlp2oql_generate(arguments: dict[str, Any]) -> dict[str, Any]:
    return nlp2oql_generate(
        arguments["prompt"],
        project_dir=arguments.get("project_dir"),
        project_root=arguments.get("project_root"),
        use_llm=bool(arguments.get("use_llm", False)),
        validate=bool(arguments.get("validate", True)),
    )


def tool_nlp2oql_run(arguments: dict[str, Any]) -> dict[str, Any]:
    return nlp2oql_run(
        arguments["prompt"],
        project_dir=arguments.get("project_dir"),
        project_root=arguments.get("project_root"),
        backend=arguments.get("backend"),
        execute=bool(arguments.get("execute", False)),
        url=arguments.get("url"),
        captcha_solver=bool(arguments.get("captcha_solver", False)),
        visual_mode=bool(arguments.get("visual_mode", False)),
    )


TOOL_DISPATCH: dict[str, Any] = {
    "koru_nlp2oql_generate": tool_nlp2oql_generate,
    "koru_nlp2oql_run": tool_nlp2oql_run,
}
