"""Tests for dsl2coru UI_* verbs (imgl delegation)."""

from __future__ import annotations

from unittest.mock import patch

from dsl2coru.grammar import parse_line, to_text
from dsl2coru.handlers.ui import run_ui_command


def test_ui_type_grammar() -> None:
    payload = parse_line('UI_TYPE "hello" IN "Chat input" WINDOW region-bottom')
    assert payload["verb"] == "UI_TYPE"
    assert payload["value"] == "hello"
    assert payload["field"] == "Chat input"
    assert payload["window"] == "region-bottom"
    text = to_text(payload)
    assert "UI_TYPE" in text
    assert "hello" in text


def test_ui_key_grammar() -> None:
    payload = parse_line("UI_KEY ctrl+Return")
    assert payload["verb"] == "UI_KEY"
    assert payload["keys"] == "ctrl+Return"


def test_run_ui_command_delegates(monkeypatch) -> None:
    calls: list[str] = []

    def fake_execute(prompt: str, **kwargs):
        calls.append(prompt)
        return {"ok": True, "backend": "imgl", "output": prompt}

    with patch("koru.integrations.imgl_client.imgl_available", return_value=True), patch(
        "koru.integrations.imgl_client.execute_nl",
        side_effect=fake_execute,
    ):
        payload = parse_line('UI_TYPE "test" IN "Chat input"')
        result = run_ui_command(payload, line='UI_TYPE "test" IN "Chat input"')
    assert result.ok
    assert calls == ["wpisz test w Chat input"]
