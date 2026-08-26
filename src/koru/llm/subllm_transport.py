"""Policy-resolved LLM transport for Koru autonomous decisions."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SubLlmResult:
    returncode: int
    stdout: str
    stderr: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


def _error(message: str, *, model: str = "zai/glm-5.3") -> SubLlmResult:
    return SubLlmResult(
        returncode=1,
        stdout="",
        stderr=message,
        model=model,
        raw={"provider": "subllm", "model": model},
    )


def _runtime() -> tuple[Callable[..., Any], Callable[..., Any], Callable[..., Any]]:
    from litellm import completion
    from subllm import merged_environment, resolve

    return completion, merged_environment, resolve


def _usage_dict(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return dict(usage.model_dump())
    if isinstance(usage, Mapping):
        return dict(usage)
    return {}


def _content(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    if message is None:
        return ""
    return str(getattr(message, "content", "") or "")


def run_subllm_messages(
    messages: Sequence[Mapping[str, Any]],
    project: Path,
    *,
    route_function: str,
    timeout_seconds: float | None = None,
    credential_override: str | None = None,
) -> SubLlmResult:
    """Resolve a Koru route through SubLLM and execute it with LiteLLM."""
    try:
        completion, merged_environment, resolve = _runtime()
    except ImportError as exc:
        return _error(
            "SubLLM transport is unavailable; install "
            "'subactor-subllm>=1.3.1' before running Koru LLM work "
            f"({exc})"
        )

    try:
        environment = merged_environment(cwd=project)
        if credential_override:
            environment = dict(environment)
            environment["ZAI_API_KEY"] = credential_override
        route = resolve(
            "koru-agent",
            route_function,
            environ=environment,
        )
        kwargs = route.litellm_kwargs()
        response = completion(
            **kwargs,
            messages=[dict(message) for message in messages],
            timeout=timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - transport failures become queue evidence
        return _error(
            f"SubLLM refused or failed Koru route koru-agent/{route_function}: {exc}"
        )

    content = _content(response)
    model = str(route.litellm_model)
    if not content:
        return _error("SubLLM returned no assistant content", model=model)
    return SubLlmResult(
        returncode=0,
        stdout=content,
        stderr="",
        model=model,
        usage=_usage_dict(response),
        raw={
            "provider": route.provider,
            "model": route.wire_model,
            "application": route.application,
            "function": route.function,
            "transport": route.transport,
        },
    )


def run_subllm(
    prompt: str,
    project: Path,
    *,
    route_function: str,
    system_prompt: str | None = None,
    timeout_seconds: float | None = None,
    credential_override: str | None = None,
) -> SubLlmResult:
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return run_subllm_messages(
        messages,
        project,
        route_function=route_function,
        timeout_seconds=timeout_seconds,
        credential_override=credential_override,
    )


__all__ = ["SubLlmResult", "run_subllm", "run_subllm_messages"]
