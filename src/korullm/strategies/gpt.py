"""OpenAI / GPT LLM strategy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from korullm.strategies.base import DriveFailureAssessment, LlmCapabilities, LlmStrategy
from korullm.strategies.base import StaticLlmIdentityMixin
from korullm.strategies.ide_chat import IdeChatStrategy
from korullm.strategies.registry import register_llm_strategy


@dataclass(frozen=True)
class GptStrategy(StaticLlmIdentityMixin, LlmStrategy):
    _delegate: IdeChatStrategy = IdeChatStrategy()

    LLM_ID = "openai"
    LLM_LABEL = "OpenAI / GPT"

    def matches_environment(self) -> bool:
        return bool(os.environ.get("OPENAI_MODEL", "").strip())

    def capabilities(self) -> LlmCapabilities:
        return self._delegate.capabilities()

    def assess_drive_failure(
        self,
        reply: dict[str, Any],
        *,
        attempt: int,
        max_attempts: int,
    ) -> DriveFailureAssessment:
        return self._delegate.assess_drive_failure(
            reply,
            attempt=attempt,
            max_attempts=max_attempts,
        )

    def idle_marker_patterns(self) -> tuple[str, ...]:
        return (
            *self._delegate.idle_marker_patterns(),
            "gpt is thinking",
            "reasoning",
        )


register_llm_strategy(GptStrategy())

__all__ = ["GptStrategy"]
