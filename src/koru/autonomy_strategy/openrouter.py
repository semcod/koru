"""Optional OpenRouter caller for strategy-planning prompts."""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class OpenRouterStrategyResponse:
    ok: bool
    content: str
    error: str = ""


def call_openrouter_json(
    prompt: str,
    *,
    system_prompt: str = "Return only valid JSON.",
    model: str = "qwen/qwen3-coder-next",
    api_key: str | None = None,
    timeout_seconds: float = 30.0,
) -> OpenRouterStrategyResponse:
    """Low-level OpenRouter chat completion returning raw assistant text."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return OpenRouterStrategyResponse(
            ok=False,
            content="",
            error="OPENROUTER_API_KEY is not set",
        )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        OPENROUTER_CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except OSError as exc:
        return OpenRouterStrategyResponse(ok=False, content="", error=str(exc))
    try:
        content = str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        return OpenRouterStrategyResponse(
            ok=False,
            content="",
            error=f"unexpected OpenRouter response: {exc}",
        )
    return OpenRouterStrategyResponse(ok=True, content=content)


def ask_openrouter_for_strategy_patch(
    prompt: str,
    *,
    model: str = "qwen/qwen3-coder-next",
    api_key: str | None = None,
    timeout_seconds: float = 30.0,
) -> OpenRouterStrategyResponse:
    """Call OpenRouter explicitly; never used by default autonomous cycles."""
    return call_openrouter_json(
        prompt,
        system_prompt="Return only reviewable YAML or unified diff output.",
        model=model,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )


__all__ = [
    "OpenRouterStrategyResponse",
    "ask_openrouter_for_strategy_patch",
    "call_openrouter_json",
]
