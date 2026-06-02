"""``LlmStrategy`` contract for drive-retry and idle-detection policy."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal
from typing import ClassVar

DriveRetryKind = Literal[
    "stop",
    "stop_manual_focus",
    "skip_cooldown",
    "retry_focus",
    "retry_submit",
    "retry_plugin",
]


@dataclass(frozen=True)
class LlmCapabilities:
    """What this LLM backend can tell Koru about chat state."""

    supports_input_busy_probe: bool = True
    supports_submit_verification: bool = True
    supports_focus_diagnostics: bool = True


@dataclass(frozen=True)
class DriveFailureAssessment:
    """Structured outcome of ``LlmStrategy.assess_drive_failure``.

    The decision engine maps ``kind`` to operator banners and sleep
  behaviour. ``failure_signature`` feeds the dedup loop in
    ``autonomous_cycle_drive_retry``.
    """

    kind: DriveRetryKind
    failure_signature: str = ""
    warn_banner: str | None = None
    """One of ``focus`` / ``submit`` / ``plugin`` / ``manual_focus`` / ``None``."""
    sleep_seconds: float = 5.0
    detail: str = ""


class LlmStrategy(ABC):
    """Per-LLM knowledge object."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Canonical id, e.g. ``"ide_chat"`` or ``"openai"``."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable label."""

    @abstractmethod
    def matches_environment(self) -> bool:
        """``True`` when env vars indicate this backend is active."""

    @abstractmethod
    def capabilities(self) -> LlmCapabilities:
        """Return capability flags for this backend."""

    @abstractmethod
    def assess_drive_failure(
        self,
        reply: dict[str, Any],
        *,
        attempt: int,
        max_attempts: int,
    ) -> DriveFailureAssessment:
        """Decide how the autonomous loop should react to a failed drive."""

    def idle_marker_patterns(self) -> tuple[str, ...]:
        """Substrings that indicate the IDE-side LLM is still working."""
        return (
            "thinking",
            "generating",
            "working",
            "please wait",
        )

    def prompt_envelope(self, text: str) -> str:
        """Optional wrapper applied before paste/submit."""
        return text

    @staticmethod
    def _reply_message(reply: dict[str, Any]) -> str:
        return str(reply.get("message") or "").strip().lower()

    @staticmethod
    def _reply_verification(reply: dict[str, Any]) -> str:
        return str(reply.get("verification") or "").strip().lower()

    @staticmethod
    def _reply_reason(reply: dict[str, Any]) -> str:
        return str(reply.get("reason") or "").strip().lower()

    @staticmethod
    def failure_signature(reply: dict[str, Any]) -> str:
        msg = str(reply.get("message") or "").strip().lower()
        verification = str(reply.get("verification") or "").strip().lower()
        reason = str(reply.get("reason") or "").strip().lower()
        return f"{verification}|{reason}|{msg[:200]}"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} id={self.id!r}>"


class StaticLlmIdentityMixin:
    """Provide ``id``/``label`` from class-level constants."""

    LLM_ID: ClassVar[str] = ""
    LLM_LABEL: ClassVar[str] = ""

    @property
    def id(self) -> str:
        return self.LLM_ID

    @property
    def label(self) -> str:
        return self.LLM_LABEL


__all__ = [
    "DriveFailureAssessment",
    "DriveRetryKind",
    "LlmCapabilities",
    "LlmStrategy",
    "StaticLlmIdentityMixin",
]
