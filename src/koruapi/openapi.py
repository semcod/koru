"""OpenAPI 3.0 document for the koruapi HTTP server."""

from __future__ import annotations

from typing import Any

from .integrations import list_integrations


def build_openapi_document(*, host: str = "127.0.0.1", port: int = 8790) -> dict[str, Any]:
    """Build OpenAPI 3.0 JSON for ``koruapi`` integration HTTP API."""
    base = f"http://{host}:{port}"
    integration_props = {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "transport": {"type": "string"},
        "methods": {"type": "array", "items": {"type": "string"}},
        "cli_equivalent": {"type": "string", "nullable": True},
        "mcp_tool": {"type": "string", "nullable": True},
        "tags": {"type": "array", "items": {"type": "string"}},
    }
    integration_ids = [s.id for s in list_integrations()]
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "koruapi",
            "version": "0.1.0",
            "description": (
                "HTTP API for koru integrations (scan, queue, DSL, MCP tools, quality gates)."
            ),
        },
        "servers": [{"url": base}],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {
                        "200": {
                            "description": "Service is up",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "ok": {"type": "boolean"},
                                            "service": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "/api/v1/integrations": {
                "get": {
                    "summary": "List integration catalog",
                    "parameters": [
                        {
                            "name": "tag",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Filter integrations by tag.",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Integration list",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "ok": {"type": "boolean"},
                                            "integrations": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": integration_props,
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "/api/v1/invoke": {
                "post": {
                    "summary": "Invoke an integration",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["integration_id"],
                                    "properties": {
                                        "integration_id": {
                                            "type": "string",
                                            "enum": integration_ids,
                                            "description": "Integration id (alias: id).",
                                        },
                                        "id": {
                                            "type": "string",
                                            "description": "Alias for integration_id.",
                                        },
                                        "method": {
                                            "type": "string",
                                            "default": "run",
                                        },
                                        "project": {
                                            "type": "string",
                                            "description": "Project root path.",
                                        },
                                        "body": {
                                            "type": "object",
                                            "additionalProperties": True,
                                        },
                                        "payload": {
                                            "type": "object",
                                            "additionalProperties": True,
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "responses": {
                        "200": {"description": "Invocation succeeded"},
                        "400": {"description": "Invalid request or invoke error"},
                        "500": {"description": "Internal error"},
                    },
                },
            },
            "/api/v1/ide/commands": {
                "get": {
                    "summary": "IDE command catalog",
                    "parameters": [
                        {
                            "name": "ide",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "IDE id or all.",
                        },
                        {
                            "name": "for_llm",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "boolean"},
                            "description": "Return compact LLM-oriented catalog.",
                        },
                    ],
                    "responses": {"200": {"description": "IDE command catalog"}},
                },
            },
            "/api/v1/ide/scenario-schema": {
                "get": {
                    "summary": "IDE command scenario JSON Schema",
                    "responses": {"200": {"description": "Scenario schema"}},
                },
            },
            "/api/v1/openapi.json": {
                "get": {
                    "summary": "This OpenAPI document",
                    "responses": {"200": {"description": "OpenAPI JSON"}},
                },
            },
        },
        "components": {
            "schemas": {
                "Integration": {
                    "type": "object",
                    "properties": integration_props,
                },
            },
        },
    }
