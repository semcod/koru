"""MCP stdio server (koru mcp-serve) — canonical: :mod:`koruapi.mcp_server`."""

from __future__ import annotations

from koruapi.mcp_server import TOOLS, mcp_serve_main, run_stdio

__all__ = ["TOOLS", "mcp_main", "mcp_serve_main", "run_stdio"]


def mcp_main(argv: list[str] | None = None) -> int:
    """Entry point for ``koru mcp-serve`` and ``koru api mcp``."""
    from koru.activity_log import activity

    activity("MCP", "starting stdio MCP server (koru_list_tickets, koru_run_ticket, …)")
    return mcp_serve_main(argv or [])
