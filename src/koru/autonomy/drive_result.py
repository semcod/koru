"""Typed compatibility contract for autonomous drive attempts.

The autonomous loop still receives backend replies as loose dictionaries from
the IDE plugin, vdisplay, imgl, gillm, nlp2uri and OS-injector paths. This
module provides one normalized view over that legacy shape without changing the
backend APIs yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping


DriveStatus = Literal["ok", "failed", "skipped"]

_SUBMIT_UNVERIFIED_VERIFICATIONS = {"submit_unverified", "submit_failed"}


@dataclass(frozen=True)
class DriveAttemptResult:
    """Normalized result of one autonomous IDE drive attempt.

    ``raw`` intentionally preserves the original backend reply so existing
    telemetry and recovery code can keep consuming legacy fields while the
    orchestrator migrates toward typed decisions.
    """

    ok: bool
    status: DriveStatus
    reason_code: str
    backend: str | None = None
    transport: str | None = None
    verification: str = ""
    submitted: bool | None = None
    capture_confirmed: bool | None = None
    retryable: bool = False
    safe_to_redrive: bool = False
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_reply(
        cls,
        reply: Mapping[str, Any] | None,
        *,
        ok: bool | None = None,
    ) -> "DriveAttemptResult":
        """Build a normalized attempt from a legacy backend reply dict."""
        raw = dict(reply or {})
        resolved_ok = bool(raw.get("ok", True) if ok is None else ok)
        verification = str(raw.get("verification") or "").strip().lower()
        message = str(raw.get("message") or raw.get("error") or "").strip()
        manual_focus = _reply_requires_manual_chat_focus(raw)
        submit_unverified = verification in _SUBMIT_UNVERIFIED_VERIFICATIONS
        reason_code = _reason_code(
            raw,
            ok=resolved_ok,
            verification=verification,
            manual_focus=manual_focus,
        )
        status: DriveStatus
        if resolved_ok:
            status = "ok"
        elif manual_focus:
            status = "skipped"
        else:
            status = "failed"
        safe_to_redrive = bool(
            not resolved_ok
            and not manual_focus
            and not submit_unverified
            and raw.get("safe_to_redrive", True)
        )
        retryable = bool(raw.get("retryable", safe_to_redrive))
        return cls(
            ok=resolved_ok,
            status=status,
            reason_code=reason_code,
            backend=_optional_str(raw.get("backend")),
            transport=_optional_str(raw.get("transport") or raw.get("fallback_from")),
            verification=verification,
            submitted=_optional_bool(raw.get("submitted")),
            capture_confirmed=_extract_capture_confirmed(raw),
            retryable=retryable,
            safe_to_redrive=safe_to_redrive,
            message=message,
            raw=raw,
        )

    @property
    def requires_manual_focus(self) -> bool:
        return self.reason_code == "manual_focus"

    @property
    def is_submit_unverified(self) -> bool:
        return self.verification in _SUBMIT_UNVERIFIED_VERIFICATIONS

    def legacy_autopilot_status(self) -> str:
        """Return the historical status string consumed by older call sites."""
        if self.ok:
            return "ok"
        if self.requires_manual_focus:
            return "skipped(manual_focus)"
        if self.is_submit_unverified:
            return f"failed({self.verification})"
        return "failed"


def _reason_code(
    raw: Mapping[str, Any],
    *,
    ok: bool,
    verification: str,
    manual_focus: bool,
) -> str:
    if ok:
        return "ok"
    if manual_focus:
        return "manual_focus"
    if verification:
        return verification
    for key in ("failure_kind", "reason", "type"):
        value = str(raw.get(key) or "").strip().lower()
        if value:
            return _slug(value)
    message = str(raw.get("message") or raw.get("error") or "").strip().lower()
    return _slug(message) if message else "drive_failed"


def _reply_requires_manual_chat_focus(reply: Mapping[str, Any]) -> bool:
    msg = str(reply.get("message") or "").lower()
    if "chat input is not focused/open" not in msg:
        return False
    diagnostics = reply.get("diagnostics")
    if not isinstance(diagnostics, Mapping):
        return False
    candidates = diagnostics.get("focusOpenCandidates")
    return isinstance(candidates, list) and not candidates


def _extract_capture_confirmed(reply: Mapping[str, Any]) -> bool | None:
    direct = _optional_bool(reply.get("capture_confirmed"))
    if direct is not None:
        return direct
    for key in ("photo_vql_observe", "capture_provenance", "ide_control"):
        value = reply.get(key)
        if not isinstance(value, Mapping):
            continue
        nested_direct = _optional_bool(value.get("capture_confirmed"))
        if nested_direct is not None:
            return nested_direct
        nested_provenance = value.get("capture_provenance")
        if isinstance(nested_provenance, Mapping):
            nested = _optional_bool(nested_provenance.get("capture_confirmed"))
            if nested is not None:
                return nested
    return None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _slug(value: str) -> str:
    parts = []
    previous_sep = False
    for char in value.lower():
        if char.isalnum():
            parts.append(char)
            previous_sep = False
        elif not previous_sep:
            parts.append("_")
            previous_sep = True
    return "".join(parts).strip("_")[:80] or "drive_failed"


__all__ = ["DriveAttemptResult", "DriveStatus"]
