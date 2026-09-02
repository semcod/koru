"""Deprecated aliases of the canonical :mod:`mcp2koru.server`."""

from mcp2koru.server import KoruMCPServer, create_server, run_server

CoruMCPServer = KoruMCPServer

__all__ = ["CoruMCPServer", "create_server", "run_server"]
