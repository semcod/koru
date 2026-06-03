"""OpenAI Codex CLI strategy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from koru.sllm_bridge import shell_agent_available
from korullm.strategies.base import (
    DriveFailureAssessment,
    LlmCapabilities,
    LlmStrategy,
    StaticLlmIdentityMixin,
)
from korullm.strategies.ide_chat import IdeChatStrategy
from korullm.strategies.registry import register_llm_strategy


@dataclass(frozen=True)
class CodexStrategy(StaticLlmIdentityMixin, LlmStrategy):
    _delegate: IdeChatStrategy = IdeChatStrategy()

    LLM_ID = "codex"
    LLM_LABEL = "OpenAI Codex CLI"

    def matches_environment(self) -> bool:
        if os.environ.get("KORU_LLM_PROVIDER", "").strip().lower() == "codex":
            return True
        if os.environ.get("KORU_LLM_BACKEND", "").strip().lower() == "codex":
            return True
        if os.environ.get("CODEX_HOME", "").strip():
            return True
        if any(
            os.environ.get(key, "").strip()
            for key in ("OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL")
        ):
            return False
        return shell_agent_available("codex")

    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities(
            supports_input_busy_probe=True,
            supports_submit_verification=True,
            supports_focus_diagnostics=False,
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
        if assessment.kind == "stop_manual_focus":
            return DriveFailureAssessment(
                kind="retry_focus",
                failure_signature=assessment.failure_signature,
                warn_banner="focus",
                detail="codex: no focus-open diagnostics — retry focus anyway",
            )
        return assessment

    def idle_marker_patterns(self) -> tuple[str, ...]:
        return (
            *self._delegate.idle_marker_patterns(),
            "codex",
            "executing",
            "running command",
        )

    def prompt_envelope(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("# ") or stripped.startswith("## "):
            return text
        return f"# Task\n\n{text}"


register_llm_strategy(CodexStrategy())

__all__ = ["CodexStrategy"]
