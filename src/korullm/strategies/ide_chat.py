"""Default IDE-embedded chat LLM strategy.

This is the path Koru uses when prompts go into Cursor / VS Code /
Windsurf chat via the autopilot plugin. It owns the retry heuristics
that previously lived as ``_reply_needs_*`` helpers in
``autonomous_cycle_drive_retry``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from korullm.strategies.base import (
    DriveFailureAssessment,
    LlmCapabilities,
    LlmStrategy,
    StaticLlmIdentityMixin,
)
from korullm.strategies.registry import register_llm_strategy


@dataclass(frozen=True)
class IdeChatStrategy(StaticLlmIdentityMixin, LlmStrategy):
    LLM_ID = "ide_chat"
    LLM_LABEL = "IDE embedded chat"

    def matches_environment(self) -> bool:
        """Fallback strategy — matches when no explicit LLM env is set."""
        import os

        for key in (
            "KORU_LLM_PROVIDER",
            "KORU_LLM_BACKEND",
            "OPENAI_MODEL",
            "ANTHROPIC_MODEL",
            "OLLAMA_MODEL",
            "CODEX_HOME",
        ):
            if os.environ.get(key, "").strip():
                return False
        return True

    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities()

    def assess_drive_failure(
        self,
        reply: dict[str, Any],
        *,
        attempt: int,
        max_attempts: int,
    ) -> DriveFailureAssessment:
        signature = self.failure_signature(reply)
        msg = self._reply_message(reply)

        if "no connected autopilot plugin" in msg:
            return DriveFailureAssessment(kind="stop", failure_signature=signature)

        if self._reply_verification(reply) == "input_busy":
            return DriveFailureAssessment(
                kind="skip_cooldown",
                failure_signature=signature,
                detail="chat_input_not_empty",
            )
        if self._reply_reason(reply) == "chat_input_not_empty":
            return DriveFailureAssessment(
                kind="skip_cooldown",
                failure_signature=signature,
                detail="chat_input_not_empty",
            )

        if self._requires_manual_chat_focus(reply):
            return DriveFailureAssessment(
                kind="stop_manual_focus",
                failure_signature=signature,
                warn_banner="manual_focus",
            )

        if attempt >= max_attempts - 1:
            return DriveFailureAssessment(kind="stop", failure_signature=signature)

        if self._needs_submit_retry(reply):
            return DriveFailureAssessment(
                kind="retry_submit",
                failure_signature=signature,
                warn_banner="submit",
            )

        if "focus" in msg:
            return DriveFailureAssessment(
                kind="retry_focus",
                failure_signature=signature,
                warn_banner="focus",
            )

        if self._needs_plugin_retry(reply):
            return DriveFailureAssessment(
                kind="retry_plugin",
                failure_signature=signature,
                warn_banner="plugin",
            )

        return DriveFailureAssessment(kind="stop", failure_signature=signature)

    @staticmethod
    def _requires_manual_chat_focus(reply: dict[str, Any]) -> bool:
        msg = str(reply.get("message") or "").lower()
        if "chat input is not focused/open" not in msg:
            return False
        diagnostics = reply.get("diagnostics")
        if not isinstance(diagnostics, dict):
            return False
        candidates = diagnostics.get("focusOpenCandidates")
        return isinstance(candidates, list) and not candidates

    @staticmethod
    def _needs_submit_retry(reply: dict[str, Any]) -> bool:
        verification = str(reply.get("verification") or "").lower()
        if verification in {"submit_unverified", "submit_failed"}:
            return True
        if reply.get("submitted") is False and (
            reply.get("attempted_submit")
            or reply.get("winning_paste")
            or reply.get("submit_failure_reason")
        ):
            return True
        msg = str(reply.get("message") or "").lower()
        return "submit could not be verified" in msg or "submit failed" in msg

    @staticmethod
    def _needs_plugin_retry(reply: dict[str, Any]) -> bool:
        msg = str(reply.get("message") or "").lower()
        if "no connected autopilot plugin" in msg:
            return False
        if "focus" in msg:
            return False
        return (
            "plugin_error" in msg
            or "connection" in msg
            or "verification" in msg
            or "connected" in msg
            or str(reply.get("verification") or "").lower() == "plugin_error"
        )


register_llm_strategy(IdeChatStrategy())

__all__ = ["IdeChatStrategy"]
