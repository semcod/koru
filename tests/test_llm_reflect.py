"""Tests for :mod:`koru.llm_reflect` — the optional llx/OpenRouter bridge."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from koru.llm_reflect import (
    ReflectionResult,
    build_reflect_prompt,
    llm_reflect_enabled,
    reflect_on_chat,
)
from koruide.chat_history import ChatEvent


def _event(ts_offset: float, type_: str, text: str) -> ChatEvent:
    return ChatEvent(
        ts=time.time() + ts_offset,
        type=type_,
        ide="vscode",
        chat="default",
        text=text,
    )


def test_llm_reflect_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_LLM_REFLECT", raising=False)
    assert llm_reflect_enabled() is False


def test_llm_reflect_enabled_requires_llx_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_LLM_REFLECT", "1")
    monkeypatch.setattr("koru.llm_reflect.shutil.which", lambda _name: None)
    assert llm_reflect_enabled() is False
    monkeypatch.setattr("koru.llm_reflect.shutil.which", lambda _name: "/usr/bin/llx")
    assert llm_reflect_enabled() is True


def test_reflection_from_json_parses_done_needs_input() -> None:
    raw = '{"done": true, "needs_input": false, "summary": "produced patch"}'
    r = ReflectionResult.from_json(raw)
    assert r is not None
    assert r.done is True
    assert r.needs_input is False
    assert "patch" in r.summary


def test_reflection_from_json_returns_none_on_garbage() -> None:
    assert ReflectionResult.from_json("not json") is None
    assert ReflectionResult.from_json("123") is None
    assert ReflectionResult.from_json('"hello"') is None


def test_build_reflect_prompt_embeds_ticket_and_events() -> None:
    prompt = build_reflect_prompt(
        ticket_id="STARTER-184",
        ticket_title="CQRS + Event Sourcing",
        driven_prompt="Wprowadź separację Command/Query",
        events=[
            _event(-30, "message.sent", "Wprowadź separację Command/Query"),
            _event(-5, "message.received", "Done. Created commands/ and queries/."),
        ],
    )
    assert "STARTER-184" in prompt
    assert "CQRS + Event Sourcing" in prompt
    assert "message.sent" in prompt
    assert "message.received" in prompt
    assert "STRICTLY as JSON" in prompt


def test_reflect_on_chat_returns_none_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_LLM_REFLECT", raising=False)
    result = reflect_on_chat(
        ticket_id="X",
        ticket_title="Y",
        driven_prompt="Z",
        ide="vscode",
        events=[_event(-10, "message.sent", "hi")],
    )
    assert result is None


def test_reflect_on_chat_returns_none_when_no_recent_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_LLM_REFLECT", "1")
    monkeypatch.setattr("koru.llm_reflect.shutil.which", lambda _name: "/usr/bin/llx")
    result = reflect_on_chat(
        ticket_id="X",
        ticket_title="Y",
        driven_prompt="Z",
        ide="vscode",
        events=[],
    )
    assert result is None


def test_reflect_on_chat_parses_llx_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_LLM_REFLECT", "1")
    monkeypatch.setattr("koru.llm_reflect.shutil.which", lambda _name: "/usr/bin/llx")
    captured: dict = {}

    def fake_runner(argv: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        return subprocess.CompletedProcess(
            args=argv,
            returncode=0,
            stdout='{"done": false, "needs_input": true, "summary": "needs API key"}',
            stderr="",
        )

    result = reflect_on_chat(
        ticket_id="STARTER-184",
        ticket_title="CQRS",
        driven_prompt="Wprowadź…",
        ide="vscode",
        events=[_event(-5, "message.received", "I need OPENROUTER_API_KEY first.")],
        runner=fake_runner,
    )
    assert result is not None
    assert result.needs_input is True
    assert result.done is False
    assert captured["argv"][:2] == ["llx", "chat"]
    assert "--prompt" in captured["argv"]
    assert "--free" in captured["argv"]


def test_reflect_on_chat_handles_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_LLM_REFLECT", "1")
    monkeypatch.setattr("koru.llm_reflect.shutil.which", lambda _name: "/usr/bin/llx")

    def fake_runner(argv: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=argv, returncode=2, stdout="", stderr="boom")

    result = reflect_on_chat(
        ticket_id="X",
        ticket_title="Y",
        driven_prompt="Z",
        ide="vscode",
        events=[_event(-5, "message.sent", "hi")],
        runner=fake_runner,
    )
    assert result is None


def test_reflect_on_chat_handles_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_LLM_REFLECT", "1")
    monkeypatch.setattr("koru.llm_reflect.shutil.which", lambda _name: "/usr/bin/llx")

    def fake_runner(argv: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)

    result = reflect_on_chat(
        ticket_id="X",
        ticket_title="Y",
        driven_prompt="Z",
        ide="vscode",
        events=[_event(-5, "message.sent", "hi")],
        runner=fake_runner,
    )
    assert result is None
