"""MCP tool implementations — offline parity with bus."""

from unittest.mock import MagicMock

from dsl2coru.result import DslResult
from mcp2coru import tools


def test_coru_run_command(monkeypatch) -> None:
    mock = MagicMock(return_value=DslResult(ok=True, verb="STATUS", action="status", output="ok"))
    monkeypatch.setattr("dsl2coru.bus.dispatch", mock)
    out = tools.coru_run_command("STATUS")
    assert out["ok"] is True
    assert out["action"] == "status"


def test_coru_to_dsl(monkeypatch) -> None:
    import importlib

    def _fake(prompt: str, *, project: str = ".", **kwargs: object) -> str:
        return "STATUS"

    mod = importlib.import_module("nlp2coru.to_dsl")
    monkeypatch.setattr(mod, "to_dsl", _fake)
    assert tools.coru_to_dsl("status") == "STATUS"
