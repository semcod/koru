"""Policy-routed LLM backend for nlp2koru NL → DSL translation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

_ROUTE_FUNCTION = "nl-to-koru-dsl"


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
    llm = get_backend(backend, project=project)
    system = (
        "Convert user request to ONE dsl2koru command line. "
        "Allowed verbs: QUERY_REPAIR_HISTORY, QUERY_LANE_STATUS, VALIDATE_LANE, REPAIR_RUN, RESOLVE. "
        "Return JSON: {\"dsl\": \"...\"}"
    )
    try:
        content = llm.complete(
            model=model or "",
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
