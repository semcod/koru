"""Capture/source policy helpers extracted from ``vdisplay_client``.

Moved verbatim from the historical ``vdisplay_client`` monolith; the
facade re-exports every name, so ``from koru.integrations.vdisplay_client
import X`` keeps working. References that were ``vdisplay_client`` module
globals resolve through the facade at call time (``_vdc()``) so
``monkeypatch.setattr(vdisplay_client, ...)`` keeps steering the pipeline.
"""

from __future__ import annotations

import os
from typing import Any


def _vdc():
    """The vdisplay_client facade (imported lazily: it imports this module)."""
    import koru.integrations.vdisplay_client as m

    return m


def _capture_matches_requested_ide(ide: str) -> bool:
    return _vdc()._vr_capture_matches_requested_ide(
        ide,
        mismatch_fn=_vdc()._photo_vql_ide_capture_mismatch,
    )


def _prefer_photo_vql_chat(*, ide: str = "auto") -> bool:
    return _vdc()._vr_prefer_photo_vql_chat(
        ide=ide,
        capture_matches=_vdc()._capture_matches_requested_ide,
    )


def _vdisplay_source() -> str:
    return _vdc()._vr_vdisplay_source(source_for_ide_fn=_vdc()._vdisplay_source_for_ide)


def _annotate_prepare_drive_readiness(out: dict[str, Any]) -> None:
    return _vdc()._vr_annotate_prepare_drive_readiness(
        out,
        map_mismatch_allowed_fn=_vdc()._map_source_mismatch_actuation_allowed,
    )


def _resolve_vdisplay_source_for_ide(
    ide: str,
    *,
    probe: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    return _vdc()._vr_resolve_vdisplay_source_for_ide(
        ide,
        probe=probe,
        canonical_ide_fn=_vdc()._canonical_ide,
        desktop_probe_fn=_vdc()._desktop_probe,
        ide_default_source=_vdc()._IDE_DEFAULT_SOURCE,
    )


def _vdisplay_source_for_ide(ide: str) -> str:
    return _vdc()._vr_vdisplay_source_for_ide(
        ide,
        resolve_fn=_vdc()._resolve_vdisplay_source_for_ide,
        canonical_ide_fn=_vdc()._canonical_ide,
        ide_default_source=_vdc()._IDE_DEFAULT_SOURCE,
    )


def _prefer_ide_prompt_over_photo_vql(*, ide: str) -> bool:
    """JetBrains on Wayland: GUI map beats photo VQL when capture shows the wrong IDE."""
    canon = _vdc()._canonical_ide(ide)
    if canon not in {"jetbrains", "pycharm", "idea"}:
        return False
    if not _vdc()._capture_matches_requested_ide(ide):
        return True
    raw = os.environ.get("KORU_VDISPLAY_PREFER_PHOTO_VQL", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return True
    if raw == "auto":
        return False
    return False


def _auto_ide_control_enabled() -> bool:
    return os.environ.get("KORU_VDISPLAY_AUTO_IDE_CONTROL", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _auto_open_ide_enabled(*, ide: str = "auto") -> bool:
    raw = os.environ.get("KORU_VDISPLAY_AUTO_OPEN_IDE", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return _vdc()._canonical_ide(ide) in {"jetbrains", "pycharm", "idea"}
