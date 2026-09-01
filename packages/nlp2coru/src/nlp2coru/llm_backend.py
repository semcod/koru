"""Policy-routed LLM backend abstraction for nlp2coru."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

_ROUTE_FUNCTION = "nl-to-coru-dsl"


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


class SubLlmBackend:
    """Default backend resolved by the central SubLLM policy."""

    def __init__(self, project: str | Path | None = None) -> None:
        self._project = Path(project or ".").resolve()

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        from korullm import run_subllm_messages

        # Compatibility-only inputs are deliberately not policy selectors.
        _ = model, temperature, response_format
        result = run_subllm_messages(
            messages,
            self._project,
            route_function=_ROUTE_FUNCTION,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "central SubLLM route failed")
        return result.stdout.strip()


def get_backend(
    backend: LLMBackend | None = None,
    *,
    project: str | Path | None = None,
) -> LLMBackend:
    """Return the injected backend or the central policy backend."""
    if backend is not None:
        return backend
    return SubLlmBackend(project)
