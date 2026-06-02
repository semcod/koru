"""Typed decision contract for autonomous skip/drive policy.

The autonomous loop historically threaded ``(should_skip, skip_reason)`` tuples
through multiple modules. This file introduces a small typed payload that keeps
reason code, rendered status, and operator-facing hints together while retaining
compatibility with the old tuple interface.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AutopilotPolicyDecision:
    """Result of one policy decision used by autonomous cycle modules.

    Fields:
      should_skip: whether autopilot drive should be skipped for this cycle.
      reason_code: machine-readable reason taxonomy token.
      status: legacy status string consumed by orchestrator (e.g. ``skipped(chat_activity)``).
      because: human-readable reason for logs/trace.
      action_hint: concise next operator/system action.
    """

    should_skip: bool
    reason_code: str = ""
    status: str = ""
    because: str = ""
    action_hint: str = ""

    @classmethod
    def proceed(cls) -> "AutopilotPolicyDecision":
        return cls(should_skip=False)

    @classmethod
    def skip(
        cls,
        reason_code: str,
        *,
        because: str = "",
        action_hint: str = "",
    ) -> "AutopilotPolicyDecision":
        code = str(reason_code or "unknown").strip() or "unknown"
        return cls(
            should_skip=True,
            reason_code=code,
            status=f"skipped({code})",
            because=because,
            action_hint=action_hint,
        )

    def as_skip_tuple(self) -> tuple[bool, str]:
        """Compatibility adapter for old ``(should_skip, skip_reason)`` call sites."""
        return self.should_skip, self.status


__all__ = ["AutopilotPolicyDecision"]
