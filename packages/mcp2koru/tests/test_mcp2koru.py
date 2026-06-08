import pytest

from mcp2koru.server import KoruMCPServer


def test_mcp_server_registers() -> None:
    pytest.importorskip("mcp")
    server = KoruMCPServer(name="test-koru")
    assert server.app.name == "test-koru"
