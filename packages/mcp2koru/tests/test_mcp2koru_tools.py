"""MCP tool implementations — offline parity with bus."""

from unittest.mock import MagicMock

from dsl2koru.result import DslResult
from mcp2koru import tools


def test_koru_run_command(monkeypatch) -> None:
    mock = MagicMock(return_value=DslResult(ok=True, verb="VALIDATE_LANE", output="ok"))
    monkeypatch.setattr("dsl2koru.bus.dispatch", mock)
    out = tools.koru_run_command("VALIDATE_LANE IDE auto INSTANCE default")
    assert out["ok"] is True
    assert out["verb"] == "VALIDATE_LANE"


def test_koru_to_dsl(monkeypatch) -> None:
    import importlib

    def _fake(prompt: str, *, project: str = ".", **kwargs: object) -> str:
        return "VALIDATE_LANE IDE auto INSTANCE default"

    mod = importlib.import_module("nlp2koru.to_dsl")
    monkeypatch.setattr(mod, "to_dsl", _fake)
    assert "VALIDATE_LANE" in tools.koru_to_dsl("validate lane")
