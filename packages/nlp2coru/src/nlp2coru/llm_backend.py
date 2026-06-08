"""LLM backend abstraction for nlp2coru.

Protocol + default litellm implementation so llm.py and rewrite.py
are not coupled directly to litellm import at module load time.
"""

from __future__ import annotations

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
