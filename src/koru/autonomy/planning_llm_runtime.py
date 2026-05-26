from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any

from .planning_llm_budget import DEFAULT_MODEL


def planning_llm_enabled() -> bool:
    raw = os.environ.get("KORU_PLANNING_LLM", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def model_name() -> str:
    return os.environ.get("KORU_PLANNING_LLM_MODEL", "").strip() or DEFAULT_MODEL


def request_timeout() -> float:
    raw = os.environ.get("KORU_PLANNING_LLM_TIMEOUT", "").strip()
    try:
        return max(5.0, float(raw)) if raw else 30.0
    except ValueError:
        return 30.0


@dataclass(frozen=True)
class LlmResponse:
    ok: bool
    content: str
    error: str = ""
    cost_usd: float = 0.0
    model: str = ""
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
