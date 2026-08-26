from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from korullm import subllm as subllm_transport


def test_run_subllm_uses_policy_route_without_forcing_provider(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def complete(application, function, messages, **kwargs):
        observed.update(
            application=application,
            function=function,
            messages=messages,
            **kwargs,
        )
        return SimpleNamespace(
            content='{"ok":true}',
            provider="zai",
            model="glm-5.3",
            usage={"total_tokens": 7},
        )

    monkeypatch.setattr(
        subllm_transport,
        "_runtime",
        lambda: (complete, lambda **_kwargs: {"ZAI_API_KEY": "test-key"}),
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
    assert result.raw["transport"] == "subllm.complete"
    assert observed["application"] == "koru-agent"
    assert observed["function"] == "planning-assistant"
    assert observed["environ"] == {"ZAI_API_KEY": "test-key"}
    assert observed["timeout_seconds"] == 12
    assert observed["messages"] == [
        {"role": "system", "content": "JSON only"},
        {"role": "user", "content": "plan"},
    ]


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
    assert "subactor-subllm>=1.4.0" in result.stderr
