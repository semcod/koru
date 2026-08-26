from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from koru.llm import subllm_transport


class _Route:
    provider = "zai"
    wire_model = "glm-5.3"
    litellm_model = "zai/glm-5.3"
    application = "koru-agent"
    function = "planning-assistant"
    transport = "openai-compatible"

    def litellm_kwargs(self) -> dict[str, object]:
        return {
            "model": self.litellm_model,
            "api_key": "test-key",
            "api_base": "https://api.z.ai/api/coding/paas/v4",
        }


def test_run_subllm_uses_policy_route_without_forcing_provider(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def completion(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))],
            usage=SimpleNamespace(model_dump=lambda: {"total_tokens": 7}),
        )

    def resolve(application, function, **kwargs):
        observed["resolved"] = (application, function, kwargs)
        return _Route()

    monkeypatch.setattr(
        subllm_transport,
        "_runtime",
        lambda: (completion, lambda **_kwargs: {"ZAI_API_KEY": "test-key"}, resolve),
    )

    result = subllm_transport.run_subllm(
        "plan",
        Path("/workspace"),
        route_function="planning-assistant",
        system_prompt="JSON only",
        timeout_seconds=12,
    )

    assert result.returncode == 0
    assert result.model == "zai/glm-5.3"
    assert result.raw["provider"] == "zai"
    assert observed["resolved"] == (
        "koru-agent",
        "planning-assistant",
        {"environ": {"ZAI_API_KEY": "test-key"}},
    )
    assert observed["model"] == "zai/glm-5.3"
    assert observed["api_base"] == "https://api.z.ai/api/coding/paas/v4"
    assert observed["timeout"] == 12


def test_run_subllm_fails_closed_when_runtime_is_missing(monkeypatch) -> None:
    def unavailable():
        raise ImportError("subllm missing")

    monkeypatch.setattr(subllm_transport, "_runtime", unavailable)

    result = subllm_transport.run_subllm(
        "plan",
        Path("/workspace"),
        route_function="planning-assistant",
    )

    assert result.returncode == 1
    assert "subactor-subllm>=1.3.1" in result.stderr
