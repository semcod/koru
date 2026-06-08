"""LLM backend for nlp2koru NL → DSL translation.

Isolates litellm dependency behind an injectable LLMBackend Protocol
(mirrors nlp2coru.llm_backend for consistency across the monorepo).
"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol, runtime_checkable

from .openrouter_config import (
    get_openrouter_headers,
    get_fallback_model,
    get_ollama_base_url,
    should_use_ollama_fallback,
)


@runtime_checkable
class LLMBackend(Protocol):
    """Minimal LLM completion interface."""

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Return the assistant message content string."""
        ...


class LitellmBackend:
    """Default backend: thin wrapper around litellm.completion."""

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        import litellm  # type: ignore

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        
        # Add OpenRouter headers for app identification
        headers = get_openrouter_headers()
        if headers:
            kwargs["headers"] = headers
        
        # Try OpenRouter first, fallback to Ollama if configured
        try:
            response = litellm.completion(**kwargs)
            return (response.choices[0].message.content or "").strip()
        except Exception:
            # Check if we should use Ollama fallback
            if should_use_ollama_fallback() and model.startswith("openrouter/"):
                # Convert to Ollama model format
                ollama_model = get_fallback_model()
                ollama_base_url = get_ollama_base_url()
                
                kwargs["model"] = ollama_model
                kwargs["api_base"] = ollama_base_url
                # Remove OpenRouter headers for Ollama
                kwargs.pop("headers", None)
                
                try:
                    response = litellm.completion(**kwargs)
                    return (response.choices[0].message.content or "").strip()
                except Exception:
                    # If Ollama also fails, re-raise the original error
                    pass
            
            # Re-raise the original exception
            raise


def get_backend(backend: LLMBackend | None = None) -> LLMBackend:
    """Return the provided backend or a LitellmBackend instance."""
    if backend is not None:
        return backend
    return LitellmBackend()


def nl_to_dsl_line(
    prompt: str,
    *,
    project: str | None = None,
    model: str | None = None,
    backend: LLMBackend | None = None,
) -> str | None:
    """Convert NL prompt to a single DSL line via LLM.

    Returns the DSL string or None if conversion fails.
    """
    resolved_model = model or os.getenv("CORU_LLM_MODEL", "openrouter/qwen/qwen3-coder-next")
    llm = get_backend(backend)
    system = (
        "Convert user request to ONE dsl2koru command line. "
        "Allowed verbs: QUERY_REPAIR_HISTORY, QUERY_LANE_STATUS, VALIDATE_LANE, REPAIR_RUN, RESOLVE. "
        "Return JSON: {\"dsl\": \"...\"}"
    )
    try:
        content = llm.complete(
            model=resolved_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps({"prompt": prompt, "project": project or "."})},
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(content or "{}")
        dsl = str(data.get("dsl", "")).strip()
        return dsl or None
    except Exception:
        return None
