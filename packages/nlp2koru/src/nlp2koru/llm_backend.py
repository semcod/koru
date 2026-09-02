"""Policy-routed LLM helpers for canonical nlp2koru behavior."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

_ROUTE_FUNCTION = "nl-to-koru-dsl"
_LEGACY_ROUTE_FUNCTION = "nl-to-coru-dsl"
_VALID_ACTIONS = frozenset(
    {"auto", "ensure", "lane", "status", "doctor", "calibration", "chat", "repair", "sync"}
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
    ) -> str: ...


class SubLlmBackend:
    """Default backend resolved by central SubLLM policy."""

    def __init__(
        self,
        project: str | Path | None = None,
        *,
        route_function: str = _ROUTE_FUNCTION,
    ) -> None:
        self._project = Path(project or ".").resolve()
        self._route_function = route_function

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        from korullm import run_subllm_messages

        _ = model, temperature, response_format
        result = run_subllm_messages(messages, self._project, route_function=self._route_function)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "central SubLLM route failed")
        return result.stdout.strip()


def get_backend(
    backend: LLMBackend | None = None,
    *,
    project: str | Path | None = None,
) -> LLMBackend:
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
    """Convert a prompt to one dsl2koru line, failing safely to ``None``."""
    llm = get_backend(backend, project=project)
    system = (
        "Convert user request to ONE dsl2koru command line. "
        "Allowed verbs: QUERY_REPAIR_HISTORY, QUERY_LANE_STATUS, VALIDATE_LANE, REPAIR_RUN, RESOLVE. "
        'Return JSON: {"dsl": "..."}'
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
        dsl = str(json.loads(content or "{}").get("dsl", "")).strip()
        return dsl or None
    except Exception:
        return None


def _parse_llm_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("LLM response did not include JSON")
    return json.loads(match.group(0))


def _plan_with_route(
    text: str,
    *,
    model: str | None,
    backend: LLMBackend | None,
    route_function: str,
):
    from nlp2koru.to_dsl import KoruIntent, KoruPlan, heuristic_plan

    llm = backend or SubLlmBackend(route_function=route_function)
    prompt = (
        "Return JSON only, without fences. Format: "
        '{"action": "auto|lane|ensure|status|doctor|calibration|chat|repair|sync", '
        '"ide": "optional", "instance": "optional", "install": false}. '
        f"Prompt: {text}"
    )
    try:
        content = llm.complete(
            model=model or "",
            messages=[
                {"role": "system", "content": "You map user intent to Koru control actions."},
                {"role": "user", "content": prompt},
            ],
        )
        payload = _parse_llm_json(content)
    except Exception:
        return heuristic_plan(text)

    action = str(payload.get("action") or "status").strip().lower()
    if action not in _VALID_ACTIONS:
        action = "status"
    return KoruPlan(
        [
            KoruIntent(
                action=action,
                ide=str(payload.get("ide") or "") or None,
                instance=str(payload.get("instance") or "") or None,
                install=bool(payload.get("install", False)),
            )
        ],
        use_llm=True,
    )


def llm_plan(
    text: str,
    *,
    model: str | None = None,
    backend: LLMBackend | None = None,
):
    """Resolve a compatibility control plan through the canonical route."""
    return _plan_with_route(text, model=model, backend=backend, route_function=_ROUTE_FUNCTION)


def legacy_llm_plan(
    text: str,
    *,
    model: str | None = None,
    backend: LLMBackend | None = None,
):
    """Preserve the registered legacy route during its compatibility release."""
    return _plan_with_route(text, model=model, backend=backend, route_function=_LEGACY_ROUTE_FUNCTION)


def rewrite_chat_prompt(
    text: str,
    *,
    ide: str,
    instance: str,
    model: str | None = None,
    backend: LLMBackend | None = None,
) -> str:
    """Rewrite an IDE chat prompt through the canonical backend boundary."""
    llm = get_backend(backend)
    try:
        rewritten = llm.complete(
            model=model or "",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Rewrite the user message into a concise IDE chat prompt for coding assistant. "
                        "Preserve intent and language. Return only plain text."
                    ),
                },
                {"role": "user", "content": f"ide={ide} instance={instance}\nmessage={text}"},
            ],
        )
    except Exception:
        return text
    return rewritten or text
