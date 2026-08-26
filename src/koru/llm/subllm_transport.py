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


def _runtime() -> tuple[Callable[..., Any], Callable[..., Any]]:
    from subllm import complete, merged_environment

    return complete, merged_environment


def run_subllm_messages(
    messages: Sequence[Mapping[str, Any]],
    project: Path,
    *,
    route_function: str,
    timeout_seconds: float | None = None,
    credential_override: str | None = None,
) -> SubLlmResult:
    """Resolve and execute a Koru route through public SubLLM."""
    try:
        complete, merged_environment = _runtime()
    except ImportError as exc:
        return _error(
            "SubLLM transport is unavailable; install "
            "'subactor-subllm>=1.4.0' before running Koru LLM work "
            f"({exc})"
        )

    try:
        environment = merged_environment(cwd=project)
        if credential_override:
            environment = dict(environment)
            environment["ZAI_API_KEY"] = credential_override
        completion_kwargs: dict[str, Any] = {
            "environ": environment,
        }
        if timeout_seconds is not None:
            completion_kwargs["timeout_seconds"] = timeout_seconds
        response = complete(
            "koru-agent",
            route_function,
            [dict(message) for message in messages],
            **completion_kwargs,
        )
    except Exception as exc:  # noqa: BLE001 - transport failures become queue evidence
        return _error(
            f"SubLLM refused or failed Koru route koru-agent/{route_function}: {exc}"
        )

    content = str(response.content or "")
    model = f"{response.provider}/{response.model}"
    if not content:
        return _error("SubLLM returned no assistant content", model=model)
    return SubLlmResult(
        returncode=0,
        stdout=content,
        stderr="",
        model=model,
        usage=dict(response.usage),
        raw={
            "provider": response.provider,
            "model": response.model,
            "application": "koru-agent",
            "function": route_function,
            "transport": "subllm.complete",
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
