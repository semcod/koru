"""Registry + resolver for :class:`LlmStrategy` implementations."""

from __future__ import annotations

import os
from dataclasses import dataclass

from korullm.strategies.base import LlmStrategy

_REGISTRY: list[LlmStrategy] = []

_PROVIDER_ALIASES: dict[str, str] = {
    "koru": "ide_chat",
    "ide": "ide_chat",
    "ide_chat": "ide_chat",
    "openai": "openai",
    "gpt": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "ollama": "ollama",
    "codex": "codex",
}


def register_llm_strategy(strategy: LlmStrategy) -> None:
    for old in [s for s in _REGISTRY if s.id == strategy.id]:
        _REGISTRY.remove(old)
    _REGISTRY.append(strategy)


def get_llm_strategy(strategy_id: str) -> LlmStrategy | None:
    canonical = _PROVIDER_ALIASES.get(strategy_id.lower(), strategy_id.lower())
    for strategy in _REGISTRY:
        if strategy.id == canonical:
            return strategy
    return None


def list_llm_strategy_ids() -> tuple[str, ...]:
    return tuple(s.id for s in _REGISTRY)


def _fallback_strategy() -> LlmStrategy:
    strategy = get_llm_strategy("ide_chat")
    if strategy is not None:
        return strategy
    if not _REGISTRY:
        raise RuntimeError("korullm: no LlmStrategy registered")
    return _REGISTRY[-1]


def resolve_active_llm_strategy() -> LlmStrategy:
    """Return the strategy for the current environment."""
    strategy, _meta = resolve_llm_strategy_from_environment()
    return strategy


@dataclass(frozen=True)
class ResolvedLlmEnvironment:
    provider: str
    model: str | None
    source: str


def resolve_llm_strategy_from_environment() -> tuple[LlmStrategy, ResolvedLlmEnvironment]:
    """Resolve both the strategy object and the env metadata for profiles."""
    for key in ("KORU_LLM_PROVIDER", "KORU_LLM_BACKEND"):
        value = os.environ.get(key, "").strip()
        if not value:
            continue
        strategy = get_llm_strategy(value) or _fallback_strategy()
        return strategy, ResolvedLlmEnvironment(
            provider=strategy.id,
            model=None,
            source=key,
        )

    for key, provider_id in (
        ("OPENAI_MODEL", "openai"),
        ("ANTHROPIC_MODEL", "anthropic"),
        ("OLLAMA_MODEL", "ollama"),
    ):
        value = os.environ.get(key, "").strip()
        if not value:
            continue
        strategy = get_llm_strategy(provider_id) or _fallback_strategy()
        return strategy, ResolvedLlmEnvironment(
            provider=strategy.id,
            model=value,
            source=key,
        )

    if os.environ.get("CODEX_HOME", "").strip():
        strategy = get_llm_strategy("codex") or _fallback_strategy()
        return strategy, ResolvedLlmEnvironment(
            provider=strategy.id,
            model=None,
            source="CODEX_HOME",
        )

    strategy = _fallback_strategy()
    return strategy, ResolvedLlmEnvironment(
        provider=strategy.id,
        model=None,
        source="default",
    )


__all__ = [
    "ResolvedLlmEnvironment",
    "get_llm_strategy",
    "list_llm_strategy_ids",
    "register_llm_strategy",
    "resolve_active_llm_strategy",
    "resolve_llm_strategy_from_environment",
]
