import importlib
import sys

import pytest


def test_legacy_mcp_server_warns_and_reexports_canonical_server() -> None:
    sys.modules.pop("mcp2coru", None)
    sys.modules.pop("mcp2coru.server", None)
    with pytest.warns(DeprecationWarning, match="mcp2coru is deprecated"):
        legacy = importlib.import_module("mcp2coru.server")
    canonical = importlib.import_module("mcp2koru.server")

    assert legacy.CoruMCPServer is canonical.KoruMCPServer
    assert legacy.create_server is canonical.create_server
    assert legacy.run_server is canonical.run_server
