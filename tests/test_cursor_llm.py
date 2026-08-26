from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace

from koru.queue.context import build_project_context
from korullm import run_cursor_llm


@dataclass(frozen=True)
class _Usage:
    input_tokens: int = 12
    output_tokens: int = 7
    total_tokens: int = 19


class _Route:
    wire_model = "grok-4.6"
    model_parameters = {"effort": "xhigh", "fast": "false"}

    def cursor_sdk_kwargs(self):
        return {
            "model": {
                "id": "grok-4.6",
                "params": [
                    {"id": "effort", "value": "xhigh"},
                    {"id": "fast", "value": "false"},
                ],
            },
            "api_key": "cursor-test-key",
        }


def _install_fakes(monkeypatch, *, wait_seconds: float = 0.0):
    captured = {}

    class FakeRun:
        cancelled = False

        def wait(self):
            time.sleep(wait_seconds)
            return SimpleNamespace(
                id="run-1",
                agent_id="agent-1",
                status=SimpleNamespace(value="finished"),
                result='{"ok": true}',
                duration_ms=25,
                usage=_Usage(),
            )

        def supports(self, operation):
            return operation == "cancel"

        def cancel(self):
            self.cancelled = True

    class FakeAgent:
        def __init__(self, options):
            captured["options"] = options
            captured["run"] = FakeRun()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def send(self, prompt):
            captured["prompt"] = prompt
            return captured["run"]

    class Agent:
        @staticmethod
        def create(options):
            return FakeAgent(options)

    class Options:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    cursor_sdk = ModuleType("cursor_sdk")
    cursor_sdk.Agent = Agent
    cursor_sdk.AgentOptions = Options
    cursor_sdk.LocalAgentOptions = Options
    monkeypatch.setitem(sys.modules, "cursor_sdk", cursor_sdk)

    subllm = ModuleType("subllm")
    subllm.merged_environment = lambda *, cwd: {"CURSOR_API_KEY": "cursor-test-key"}
    subllm.resolve = lambda *args, **kwargs: _Route()
    monkeypatch.setitem(sys.modules, "subllm", subllm)
    return captured


def test_cursor_transport_uses_strict_xhigh_route_without_tools(tmp_path, monkeypatch):
    captured = _install_fakes(monkeypatch)

    result = run_cursor_llm(
        "analyse",
        tmp_path,
        route_function="planning-assistant",
        system_prompt="JSON only",
        timeout_seconds=1,
    )

    assert result.returncode == 0
    assert result.model == "grok-4.6"
    assert result.usage["total_tokens"] == 19
    assert result.raw["model_parameters"] == {"effort": "xhigh", "fast": "false"}
    assert captured["options"].model["params"][0] == {"id": "effort", "value": "xhigh"}
    assert captured["options"].tools == []
    assert captured["options"].local.cwd == str(tmp_path)
    assert "<system_instructions>\nJSON only" in captured["prompt"]


def test_cursor_transport_fails_closed_when_subllm_refuses(tmp_path, monkeypatch):
    _install_fakes(monkeypatch)
    sys.modules["subllm"].resolve = lambda *args, **kwargs: (_ for _ in ()).throw(
        RuntimeError("CURSOR_API_KEY missing")
    )

    result = run_cursor_llm("analyse", tmp_path, route_function="planning-assistant")

    assert result.returncode == 1
    assert "CURSOR_API_KEY missing" in result.stderr
    assert result.raw["provider"] == "cursor"


def test_cursor_transport_cancels_timed_out_run(tmp_path, monkeypatch):
    captured = _install_fakes(monkeypatch, wait_seconds=0.2)

    result = run_cursor_llm(
        "analyse",
        tmp_path,
        route_function="queue-executor",
        timeout_seconds=0.01,
    )

    assert result.returncode == 1
    assert "timed out" in result.stderr
    assert captured["run"].cancelled is True


def test_project_context_has_no_default_character_cap(tmp_path):
    content = "x = 1\n" * 10_000
    (tmp_path / "large.py").write_text(content, encoding="utf-8")

    result = build_project_context(
        tmp_path,
        {"prompt": "analyse", "context_files": ["large.py"]},
    )

    assert result is not None
    assert result.truncated is False
    assert content in result.text
