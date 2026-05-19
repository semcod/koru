"""Smoke tests for koruapi transport shims."""

from __future__ import annotations

from koruapi.dashboard import build_serve_parser
from koruapi.integrations import list_integrations
from koruapi.mcp import mcp_main


def test_build_serve_parser_defaults() -> None:
    args = build_serve_parser().parse_args([])
    assert args.port == 8765


def test_integrations_include_gate_regix() -> None:
    assert "gate.regix" in {s.id for s in list_integrations()}


def test_mcp_main_version_exit() -> None:
    assert mcp_main(["--version"]) == 0
