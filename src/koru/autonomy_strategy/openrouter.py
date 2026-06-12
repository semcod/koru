"""Optional OpenRouter caller for strategy-planning prompts."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# Add shared configuration to path
shared_config_path = Path(__file__).parent.parent.parent.parent.parent / "shared" / "openrouter_config.py"
if shared_config_path.exists():
    sys.path.insert(0, str(shared_config_path.parent))
    from openrouter_config import get_openrouter_headers, should_use_fallback, get_llm_config
else:
    # Fallback if shared config is not available
    def get_openrouter_headers():
        return {}
    def should_use_fallback():
        return False
    def get_llm_config():
        return {"primary": {"model": "openrouter/qwen/qwen3-coder-next"}}

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
            **get_openrouter_headers(),
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


def call_openrouter_vision(
    text_prompt: str,
    image_data_url: str,  # e.g. "data:image/png;base64,...."
    *,
    system_prompt: str = "You are a precise desktop automation agent. Given a screenshot and VQL UI description, decide the best action. Return ONLY valid minified JSON with keys: click_center (dict with int x,y), strategy (short string), confidence (float 0-1), reason (short string).",
    model: str | None = None,
    api_key: str | None = None,
    timeout_seconds: float = 60.0,
) -> OpenRouterStrategyResponse:
    """Call OpenRouter with vision (image + text). For models that support image_url content."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return OpenRouterStrategyResponse(
            ok=False,
            content="",
            error="OPENROUTER_API_KEY is not set",
        )
    if model is None:
        model = os.environ.get("LLM_MODEL", "google/gemini-flash-1.5")
    # Normalize: some .env use "openrouter/..." prefix (for registry); OR API expects "provider/model"
    if isinstance(model, str) and model.startswith("openrouter/"):
        model = model.split("/", 1)[1]
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
    payload = {
        "model": model,
        "messages": messages,
    }
    req = urllib.request.Request(
        OPENROUTER_CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            **get_openrouter_headers(),
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


__all__ = [
    "OpenRouterStrategyResponse",
    "ask_openrouter_for_strategy_patch",
    "call_openrouter_json",
    "call_openrouter_vision",
]
