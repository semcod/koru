"""An explicit shell repair cannot silently finish through central SubLLM."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from planfile import Planfile

from koru.queue import runners
from koru.queue.runner import run_next_planfile_task
from koru.queue.ticket import ticket_llm_request


def _central(monkeypatch):
    calls = []

    def complete(application, function, messages, **kwargs):
        calls.append((application, function, messages, kwargs))
        return SimpleNamespace(content="central answer", provider="test", model="central", usage={})

    monkeypatch.setattr("korullm.subllm._runtime", lambda: (complete, lambda **kwargs: {}))
    monkeypatch.setattr(runners, "probe_subllm_route", lambda *args, **kwargs: (True, "ready"))
    monkeypatch.setattr(
        "koru.tillm_bridge.drive_shell_chat",
        lambda **kwargs: pytest.fail("Unadmitted shell must never start"),
    )
    return calls


def _native_store(tmp_path, monkeypatch):
    monkeypatch.setenv("KORU_PLANFILE_CMD", f"{sys.executable} -m planfile.cli")
    monkeypatch.setenv("KORU_PLANFILE_SYNC", "0")
    monkeypatch.setenv("KORU_LLM_PROVIDER", "codex")
    monkeypatch.delenv("PLANFILE_NO_AUTONOMY_FILTER", raising=False)
    monkeypatch.delenv("CURRENT_GOAL", raising=False)
    return Planfile(str(tmp_path))


def test_explicit_provider_survives_sdk_storage_and_request(tmp_path, monkeypatch):
    store = _native_store(tmp_path, monkeypatch)
    ticket = store.create_ticket(
        "OpenCode incident repair", executor={"kind": "llm", "mode": "automatic"},
        inputs={"prompt": "repair the incident", "provider": "opencode"},
    )
    payload = Planfile(str(tmp_path)).get_ticket(ticket.id).model_dump(mode="json")
    request = ticket_llm_request(payload)
    assert request["provider"] == "opencode"
    assert request["prompt"] == "repair the incident"


@pytest.mark.parametrize("provider", [
    "opencode", " OpenCode ", "codex", "claude", "anthropic", "claude-code",
    "aider", "cline", "gemini", "gemini-cli", "qwen", "qwen-code",
    "shell", "tillm", "vendor_cli", "vendor_agent_cli",
])
def test_direct_runner_refuses_shell_without_model_or_fallback(tmp_path, monkeypatch, provider):
    calls = _central(monkeypatch)
    monkeypatch.setenv("KORU_LLM_PROVIDER", "codex")
    result = runners.run_llm_request({"prompt": "repair", "provider": provider}, tmp_path)
    assert result.returncode == 1
    assert "shell_provider_not_admitted" in result.stderr
    assert result.stdout == ""
    assert result.raw["diagnostic_code"] == "shell_provider_not_admitted"
    assert calls == []


@pytest.mark.parametrize("provider", ["opencode", "shell"])
def test_actual_native_queue_refuses_before_claim_and_model(tmp_path, monkeypatch, provider):
    store = _native_store(tmp_path, monkeypatch)
    ticket = store.create_ticket(
        "must remain pending", executor={"kind": "llm", "mode": "automatic"},
        inputs={"prompt": "repair", "provider": provider, "patch_mode": False},
    )
    before = Planfile(str(tmp_path)).get_ticket(ticket.id).model_dump(mode="json")
    calls = _central(monkeypatch)
    monkeypatch.setattr(
        "koru.queue.runner.preflight_llm_request",
        lambda *args, **kwargs: pytest.fail("Incompatible request must precede central preflight"),
    )
    outcome = run_next_planfile_task(project=tmp_path, target_ticket_id=ticket.id)
    assert outcome.status == "infrastructure_error"
    assert outcome.exit_code == 1
    assert "shell_provider_not_admitted" in outcome.message
    assert calls == []
    assert Planfile(str(tmp_path)).get_ticket(ticket.id).model_dump(mode="json") == before


@pytest.mark.parametrize("provider", [None, "", "openrouter", "legacy-provider"])
def test_central_transport_remains_for_non_shell_tickets(tmp_path, monkeypatch, provider):
    calls = _central(monkeypatch)
    monkeypatch.setenv("KORU_LLM_PROVIDER", "codex")
    payload = {"name": "legacy ticket", "inputs": {}}
    if provider is not None:
        payload["inputs"]["provider"] = provider
    request = ticket_llm_request(payload)
    if provider is None:
        assert "provider" not in request
    result = runners.run_llm_request(request, Path(tmp_path))
    assert result.returncode == 0
    assert result.stdout == "central answer"
    assert result.model == "test/central"
    assert len(calls) == 1
    assert calls[0][:3] == ("koru-agent", "queue-executor", [{"role": "user", "content": "legacy ticket"}])
