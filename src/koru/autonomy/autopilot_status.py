"""Typed parser for legacy autonomous autopilot status strings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AutopilotStatusKind = Literal["ok", "failed", "skipped", "unknown"]


@dataclass(frozen=True)
class AutopilotStatusView:
    raw: str
    kind: AutopilotStatusKind
    code: str

    @property
    def ok(self) -> bool:
        return self.kind == "ok"

    @property
    def failed(self) -> bool:
        return self.kind == "failed"

    @property
    def skipped(self) -> bool:
        return self.kind == "skipped"

    @property
    def submit_unverified(self) -> bool:
        return self.code in {"submit_unverified", "submit_failed"}

    @property
    def manual_focus(self) -> bool:
        return self.code == "manual_focus"

    @property
    def blocker_code(self) -> str:
        if self.submit_unverified:
            return "manual_send_required"
        if self.manual_focus:
            return "manual_focus_required"
        if self.skipped or self.failed:
            return self.code or self.kind
        return ""


def parse_autopilot_status(status: str | None) -> AutopilotStatusView:
    raw = str(status or "").strip()
    lower = raw.lower()
    if lower == "ok":
        return AutopilotStatusView(raw=raw, kind="ok", code="ok")
    if lower.startswith("failed(") and raw.endswith(")"):
        return AutopilotStatusView(raw=raw, kind="failed", code=_inner_code(raw))
    if lower == "failed":
        return AutopilotStatusView(raw=raw, kind="failed", code="drive_failed")
    if lower.startswith("skipped(") and raw.endswith(")"):
        return AutopilotStatusView(raw=raw, kind="skipped", code=_inner_code(raw))
    if lower == "skipped":
        return AutopilotStatusView(raw=raw, kind="skipped", code="skipped")
    return AutopilotStatusView(raw=raw, kind="unknown", code=lower or "unknown")


def _inner_code(status: str) -> str:
    return status[status.find("(") + 1 : -1].strip().lower() or "unknown"


__all__ = ["AutopilotStatusKind", "AutopilotStatusView", "parse_autopilot_status"]
