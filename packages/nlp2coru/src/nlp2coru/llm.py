"""LLM plan backend for NL → CORU DSL (via LLMBackend Protocol)."""

from __future__ import annotations

import json
import re

from .llm_backend import LLMBackend, get_backend
from .models import CoruIntent, CoruPlan

_VALID_ACTIONS = frozenset(
    {"auto", "ensure", "lane", "status", "doctor", "calibration", "chat", "repair", "sync"}
)


def _parse_llm_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("LLM response did not include JSON")
    return json.loads(match.group(0))


def llm_plan(
    text: str,
    *,
    model: str | None = None,
    backend: LLMBackend | None = None,
) -> CoruPlan:
    try:
        llm = get_backend(backend)
    except Exception:
        from .heuristic import heuristic_plan
        return heuristic_plan(text)

    prompt = (
        "Return JSON only, without fences. Format: "
        "{\"action\": \"auto|lane|ensure|status|doctor|calibration|chat|repair|sync\", "
        "\"ide\": \"optional\", \"instance\": \"optional\", \"install\": false}. "
        f"Prompt: {text}"
    )
    try:
        content = llm.complete(
            model=model or "",
            messages=[
                {"role": "system", "content": "You map user intent to CORU control actions."},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception:
        from .heuristic import heuristic_plan
        return heuristic_plan(text)

    payload = _parse_llm_json(content)
    action = str(payload.get("action") or "status").strip().lower()
    if action not in _VALID_ACTIONS:
        action = "status"
    return CoruPlan(
        [
            CoruIntent(
                action=action,
                ide=str(payload.get("ide") or "") or None,
                instance=str(payload.get("instance") or "") or None,
                install=bool(payload.get("install", False)),
            )
        ],
        use_llm=True,
    )
