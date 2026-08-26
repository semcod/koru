"""Compatibility facade for policy-resolved SubLLM strategy calls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from korullm import run_subllm, run_subllm_messages


@dataclass(frozen=True)
class OpenRouterStrategyResponse:
    ok: bool
    content: str
    error: str = ""


def call_openrouter_json(
    prompt: str,
    *,
    system_prompt: str = "Return only valid JSON.",
    model: str = "x-ai/grok-4.6",
    api_key: str | None = None,
    timeout_seconds: float = 30.0,
) -> OpenRouterStrategyResponse:
    """Resolve the Koru planning route through SubLLM.

    The historical function name is retained for callers. ``model`` is ignored
    deliberately: model authority belongs to the versioned SubLLM policy.
    """
    del model
    result = run_subllm(
        prompt,
        Path.cwd(),
        route_function="planning-assistant",
        system_prompt=system_prompt,
        timeout_seconds=timeout_seconds,
        credential_override=api_key,
    )
    return OpenRouterStrategyResponse(
        ok=result.returncode == 0,
        content=result.stdout,
        error=result.stderr,
    )


def ask_openrouter_for_strategy_patch(
    prompt: str,
    *,
    model: str = "x-ai/grok-4.6",
    api_key: str | None = None,
    timeout_seconds: float = 30.0,
) -> OpenRouterStrategyResponse:
    """Call the centrally governed SubLLM planning route."""
    return call_openrouter_json(
        prompt,
        system_prompt="Return only reviewable YAML or unified diff output.",
        model=model,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )


def call_openrouter_vision(
    text_prompt: str,
    image_data_url: str,  # e.g. "data:image/png;base64,...."
    *,
    system_prompt: str = "You are a precise desktop automation agent. Given a screenshot and VQL UI description, decide the best action. Return ONLY valid minified JSON with keys: click_center (dict with int x,y), strategy (short string), confidence (float 0-1), reason (short string).",  # noqa: E501
    model: str | None = None,
    api_key: str | None = None,
    timeout_seconds: float = 60.0,
) -> OpenRouterStrategyResponse:
    """Call the SubLLM route with image and text content."""
    del model
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text_prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        },
    ]
    result = run_subllm_messages(
        messages,
        Path.cwd(),
        route_function="planning-assistant",
        timeout_seconds=timeout_seconds,
        credential_override=api_key,
    )
    return OpenRouterStrategyResponse(
        ok=result.returncode == 0,
        content=result.stdout,
        error=result.stderr,
    )


__all__ = [
    "OpenRouterStrategyResponse",
    "ask_openrouter_for_strategy_patch",
    "call_openrouter_json",
    "call_openrouter_vision",
]
