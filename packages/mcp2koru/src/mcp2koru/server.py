"""FastMCP server for dsl2koru."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _require_fastmcp():
    try:
        from mcp.server.fastmcp import FastMCP
        return FastMCP
    except ImportError as exc:
        raise RuntimeError("Install mcp: pip install mcp") from exc


@dataclass
class KoruMCPServer:
    name: str = "koru"

    def __post_init__(self) -> None:
        FastMCP = _require_fastmcp()
        self.app = FastMCP(self.name)
        self._register_tools()

    def _register_tools(self) -> None:
        from mcp2koru import tools

        @self.app.tool()
        def koru_run_command(command: str, project: str = ".") -> dict[str, Any]:
            """Execute one dsl2koru command line."""
            return tools.koru_run_command(command, project=project)

        @self.app.tool()
        def koru_run_dsl(script: str, project: str = ".") -> list[dict[str, Any]]:
            """Execute multiline dsl2koru script."""
            return tools.koru_run_dsl(script, project=project)

        @self.app.tool()
        def koru_run_command_pb(envelope_bytes: bytes, project: str = ".") -> bytes:
            """Execute protobuf DslEnvelope; returns protobuf DslResult."""
            return tools.koru_run_command_pb(envelope_bytes, project=project)

        @self.app.tool()
        def koru_to_dsl(prompt: str, project: str = ".") -> str:
            """Map natural language to dsl2koru command line."""
            return tools.koru_to_dsl(prompt, project=project)

    def run(self) -> None:
        self.app.run()


def create_server(name: str = "koru") -> KoruMCPServer:
    return KoruMCPServer(name=name)


def run_server() -> None:
    create_server().run()


if __name__ == "__main__":
    run_server()
