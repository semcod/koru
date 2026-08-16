"""Fail-closed Cursor SDK transport resolved through SubLLM policy."""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CursorLlmResult:
    returncode: int
    stdout: str
    stderr: str
    model: str
    usage: dict[str, Any]
    raw: dict[str, Any]


def _error(message: str, *, model: str = "cursor/grok-4.6") -> CursorLlmResult:
    return CursorLlmResult(
        returncode=1,
        stdout="",
        stderr=message,
        model=model,
        usage={},
        raw={"provider": "cursor", "model": model},
    )


def _prompt_text(prompt: str, system_prompt: str | None) -> str:
    if not system_prompt:
        return prompt
    return (
        "<system_instructions>\n"
        f"{system_prompt.strip()}\n"
        "</system_instructions>\n\n"
        f"{prompt}"
    )


def _wait_for_run(run: Any, timeout_seconds: float | None) -> tuple[Any | None, str | None]:
    if timeout_seconds is None or timeout_seconds <= 0:
        return run.wait(), None

    completed: list[Any] = []
    errors: list[BaseException] = []

    def _wait() -> None:
        try:
            completed.append(run.wait())
        except BaseException as exc:  # noqa: BLE001 - transported as a failed LLM run
            errors.append(exc)

    waiter = threading.Thread(target=_wait, name="koru-cursor-run", daemon=True)
    waiter.start()
    waiter.join(timeout_seconds)
    if waiter.is_alive():
        try:
            if run.supports("cancel"):
                run.cancel()
        except Exception:  # noqa: BLE001 - timeout remains the primary failure
            pass
        return None, f"Cursor SDK run timed out after {timeout_seconds:g}s"
    if errors:
        return None, str(errors[0])
    return (completed[0] if completed else None), None


def _usage_dict(result: Any) -> dict[str, Any]:
    usage = getattr(result, "usage", None)
    return asdict(usage) if usage is not None else {}


def run_cursor_llm(
    prompt: str,
    project: Path,
    *,
    route_function: str,
    system_prompt: str | None = None,
    timeout_seconds: float | None = None,
) -> CursorLlmResult:
    """Resolve one strict Koru route and execute a tool-free local Cursor run."""
    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
        from subllm import merged_environment, resolve
    except ImportError as exc:
        return _error(
            "Cursor LLM transport is unavailable; install "
            "'subactor-subllm[cursor]>=0.7.0' before running Koru LLM work "
            f"({exc})"
        )

    try:
        environment = merged_environment(cwd=project)
        route = resolve(
            "koru-agent",
            route_function,
            provider="cursor",
            environ=environment,
        )
        cursor = route.cursor_sdk_kwargs()
    except Exception as exc:  # noqa: BLE001 - policy/credential failures must fail closed
        return _error(f"SubLLM refused Koru route koru-agent/{route_function}: {exc}")

    model = cursor["model"]
    model_id = route.wire_model
    options = AgentOptions(
        model=model,
        api_key=cursor["api_key"],
        local=LocalAgentOptions(cwd=str(project), setting_sources=[]),
        tools=[],
        name=f"koru-{route_function}",
    )
    try:
        with Agent.create(options) as agent:
            run = agent.send(_prompt_text(prompt, system_prompt))
            result, wait_error = _wait_for_run(run, timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - SDK startup failures become queue evidence
        return _error(f"Cursor SDK could not start {route_function}: {exc}", model=model_id)

    if wait_error:
        return _error(wait_error, model=model_id)
    if result is None:
        return _error("Cursor SDK returned no run result", model=model_id)

    status = str(getattr(getattr(result, "status", ""), "value", getattr(result, "status", ""))).lower()
    content = str(getattr(result, "result", "") or "")
    succeeded = status == "finished" and bool(content)
    raw = {
        "provider": "cursor",
        "model": model_id,
        "model_parameters": dict(route.model_parameters),
        "run_id": str(getattr(result, "id", "") or ""),
        "agent_id": str(getattr(result, "agent_id", "") or ""),
        "status": status,
        "duration_ms": int(getattr(result, "duration_ms", 0) or 0),
    }
    return CursorLlmResult(
        returncode=0 if succeeded else 1,
        stdout=content,
        stderr="" if succeeded else f"Cursor SDK run ended with status {status or 'unknown'}",
        model=model_id,
        usage=_usage_dict(result),
        raw=raw,
    )
