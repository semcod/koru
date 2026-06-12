"""Desktop/capture preflight contracts for autonomous GUI drives."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class DesktopCapturePreflight:
    """Normalized preflight result for screenshot/VQL based GUI control."""

    ok: bool
    ide: str
    reason_code: str = "ok"
    message: str = ""
    capture_confirmed: bool | None = None
    vql_elements: int = 0
    observe: dict[str, Any] = field(default_factory=dict)
    vql: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("vql", None)
        return data

    def failure_reply(self, *, backend: str = "vdisplay") -> dict[str, Any]:
        return {
            "ok": False,
            "backend": backend,
            "type": "error",
            "message": self.message,
            "reason": self.reason_code,
            "verification": self.reason_code,
            "capture_confirmed": self.capture_confirmed,
            "vql_elements": self.vql_elements,
            "photo_vql_observe": self.observe,
            "desktop_preflight": self.as_dict(),
        }


def prepare_vdisplay_capture_preflight(
    *,
    ide: str,
    prepare_fn: Callable[..., Mapping[str, Any]],
    load_vql_fn: Callable[..., Mapping[str, Any]],
) -> DesktopCapturePreflight:
    """Run and normalize the vdisplay photo/VQL preflight."""
    try:
        observe = dict(prepare_fn(ide=ide) or {})
    except Exception as exc:
        return DesktopCapturePreflight(
            ok=False,
            ide=ide,
            reason_code="capture_prepare_error",
            message=str(exc),
        )

    try:
        vql = dict(load_vql_fn() or {})
    except Exception as exc:
        vql = {}
        vql_load_error = str(exc)
    else:
        vql_load_error = ""

    capture_confirmed = _capture_confirmed(observe)
    vql_elements = _vql_element_count(vql)
    reason_code, message = _classify_preflight(
        observe=observe,
        capture_confirmed=capture_confirmed,
        vql_elements=vql_elements,
        vql_load_error=vql_load_error,
    )
    return DesktopCapturePreflight(
        ok=reason_code == "ok",
        ide=ide,
        reason_code=reason_code,
        message=message,
        capture_confirmed=capture_confirmed,
        vql_elements=vql_elements,
        observe=observe,
        vql=vql,
    )


def _classify_preflight(
    *,
    observe: Mapping[str, Any],
    capture_confirmed: bool | None,
    vql_elements: int,
    vql_load_error: str,
) -> tuple[str, str]:
    if observe.get("ok") is False:
        return (
            "capture_prepare_failed",
            str(observe.get("message") or observe.get("error") or "capture prepare failed"),
        )
    if capture_confirmed is False:
        reason = _capture_validation_reason(observe)
        return (
            "capture_not_confirmed",
            reason or "capture could not be confirmed for the requested IDE",
        )
    if vql_load_error:
        return ("vql_load_failed", vql_load_error)
    if vql_elements <= 0:
        return ("vql_empty", "photo VQL has no UI elements")
    return ("ok", "desktop capture preflight passed")


def _capture_confirmed(observe: Mapping[str, Any]) -> bool | None:
    direct = _optional_bool(observe.get("capture_confirmed"))
    if direct is not None:
        return direct
    for key in ("capture_provenance", "ide_control"):
        value = observe.get(key)
        if isinstance(value, Mapping):
            nested = _optional_bool(value.get("capture_confirmed"))
            if nested is not None:
                return nested
    return None


def _capture_validation_reason(observe: Mapping[str, Any]) -> str:
    validation = observe.get("capture_validation")
    if isinstance(validation, Mapping):
        for key in ("reason", "message", "error"):
            value = str(validation.get(key) or "").strip()
            if value:
                return value
    for key in ("reason", "message", "error"):
        value = str(observe.get(key) or "").strip()
        if value:
            return value
    return ""


def _vql_element_count(vql: Mapping[str, Any]) -> int:
    elements = vql.get("ui_elements")
    if isinstance(elements, list):
        return len(elements)
    raw_elements = vql.get("elements")
    if isinstance(raw_elements, list):
        return len(raw_elements)
    if isinstance(raw_elements, int):
        return raw_elements
    return 0


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


__all__ = ["DesktopCapturePreflight", "prepare_vdisplay_capture_preflight"]
