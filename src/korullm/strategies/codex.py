"""OpenAI Codex CLI strategy."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Any

from korullm.strategies.base import DriveFailureAssessment, LlmCapabilities, LlmStrategy
from korullm.strategies.ide_chat import IdeChatStrategy
from korullm.strategies.registry import register_llm_strategy


@dataclass(frozen=True)
class CodexStrategy(LlmStrategy):
    _delegate: IdeChatStrategy = IdeChatStrategy()

    @property
    def id(self) -> str:
        return "codex"

    @property
    def label(self) -> str:
        return "OpenAI Codex CLI"

    def matches_environment(self) -> bool:
        import os

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
        return shutil.which("codex") is not None

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
