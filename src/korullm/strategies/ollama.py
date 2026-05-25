"""Ollama local LLM strategy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from korullm.strategies.base import DriveFailureAssessment, LlmCapabilities, LlmStrategy
from korullm.strategies.ide_chat import IdeChatStrategy
from korullm.strategies.registry import register_llm_strategy


@dataclass(frozen=True)
class OllamaStrategy(LlmStrategy):
    _delegate: IdeChatStrategy = IdeChatStrategy()

    @property
    def id(self) -> str:
        return "ollama"

    @property
    def label(self) -> str:
        return "Ollama"

    def matches_environment(self) -> bool:
        return bool(os.environ.get("OLLAMA_MODEL", "").strip())

    def capabilities(self) -> LlmCapabilities:
        caps = self._delegate.capabilities()
        return LlmCapabilities(
            supports_input_busy_probe=caps.supports_input_busy_probe,
            supports_submit_verification=False,
            supports_focus_diagnostics=caps.supports_focus_diagnostics,
        )

    def assess_drive_failure(
        self,
        reply: dict[str, Any],
        *,
        attempt: int,
        max_attempts: int,
    ) -> DriveFailureAssessment:
        assessment = self._delegate.assess_drive_failure(
            reply,
            attempt=attempt,
            max_attempts=max_attempts,
        )
        if assessment.kind == "retry_submit":
            return DriveFailureAssessment(
                kind="retry_plugin",
                failure_signature=assessment.failure_signature,
                warn_banner="plugin",
                detail="ollama: submit verification unreliable — retry via plugin",
            )
        return assessment

    def idle_marker_patterns(self) -> tuple[str, ...]:
        return (
            *self._delegate.idle_marker_patterns(),
            "ollama",
            "loading model",
        )


register_llm_strategy(OllamaStrategy())

__all__ = ["OllamaStrategy"]
