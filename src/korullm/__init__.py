"""Koru LLM backend strategies.

Each LLM provider (IDE chat, Codex, Claude, GPT, Ollama) owns its own
retry/idle/prompt-envelope policy. The autonomous loop must not branch
on env var names inline — it asks the registry.
"""

from korullm.strategies.base import (
    DriveFailureAssessment,
    LlmCapabilities,
    LlmStrategy,
)
from korullm.strategies import (  # noqa: F401 — register concrete strategies
    claude,
    codex,
    gpt,
    ide_chat,
    ollama,
)
from korullm.strategies.registry import (
    get_llm_strategy,
    list_llm_strategy_ids,
    register_llm_strategy,
    resolve_active_llm_strategy,
    resolve_llm_strategy_from_environment,
)

__all__ = [
    "DriveFailureAssessment",
    "LlmCapabilities",
    "LlmStrategy",
    "get_llm_strategy",
    "list_llm_strategy_ids",
    "register_llm_strategy",
    "resolve_active_llm_strategy",
    "resolve_llm_strategy_from_environment",
]
