"""Per-IDE adapters for autopilot bridge diagnostics and remediation."""

from __future__ import annotations

from koru.ide_adapters.base import (
    ActivationReport,
    BridgeStatus,
    Hypothesis,
    Remediation,
    SettingsReport,
)
from koru.ide_adapters.registry import get_adapter, supported_adapter_ids

__all__ = [
    "ActivationReport",
    "BridgeStatus",
    "Hypothesis",
    "Remediation",
    "SettingsReport",
    "get_adapter",
    "supported_adapter_ids",
]
