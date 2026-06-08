import pytest

from mcp2coru.server import CoruMCPServer


def test_mcp_server_registers() -> None:
    pytest.importorskip("mcp")
    server = CoruMCPServer(name="test-coru")
    assert server.app.name == "test-coru"
