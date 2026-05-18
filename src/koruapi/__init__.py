"""koruapi — HTTP and discovery layer for all koru integrations.

Exposes a unified catalog of integrations (planfile, queue, scan, autopilot,
MCP tools, serve dashboard, autonomous, DSL, …) and a stdlib HTTP API to
invoke them. Heavy logic stays in :mod:`koru` / :mod:`korudsl` / :mod:`koruide`.
"""

from __future__ import annotations

from .dashboard import dashboard_main
from .integrations import INTEGRATIONS, IntegrationSpec, list_integrations
from .invoke import InvokeError, invoke_integration
from .local import local_main
from .mcp import mcp_main

__all__ = [
    "INTEGRATIONS",
    "IntegrationSpec",
    "InvokeError",
    "dashboard_main",
    "invoke_integration",
    "list_integrations",
    "local_main",
    "mcp_main",
]
