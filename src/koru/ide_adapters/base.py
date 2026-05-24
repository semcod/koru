"""Shared types for IDE bridge diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RemediationKind = Literal["auto", "manual", "command"]


@dataclass(frozen=True)
class Remediation:
    kind: RemediationKind
    summary: str
    command: str | None = None
    requires_ide_closed: bool = False


@dataclass(frozen=True)
class Hypothesis:
    id: str
    confidence: float
    evidence: str
    remediation: Remediation


@dataclass(frozen=True)
class ActivationReport:
    extension_installed: bool | None
    extension_active: bool | None
    extension_id: str
    hypotheses: tuple[Hypothesis, ...] = ()


@dataclass(frozen=True)
class SettingsReport:
    expected_socket: str
    user_socket: str | None
    workspace_socket: str | None
    mismatch: bool
    workspace_settings_path: str | None = None
    user_settings_path: str | None = None


@dataclass
class BridgeStatus:
    ide: str
    socket_path: str
    daemon_running: bool
    plugins_connected: bool
    project: str | None = None
    activation: ActivationReport | None = None
    settings: SettingsReport | None = None
    hypotheses: list[Hypothesis] = field(default_factory=list)
    fixes_applied: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.daemon_running and self.plugins_connected

    def top_hypothesis(self) -> Hypothesis | None:
        if not self.hypotheses:
            return None
        return max(self.hypotheses, key=lambda h: h.confidence)

    def operator_detail(self) -> str:
        if self.ready:
            return f"plugin połączony (ide={self.ide})"
        top = self.top_hypothesis()
        if top is not None:
            return f"{top.evidence} → {top.remediation.summary}"
        if not self.daemon_running:
            return f"daemon nie działa na {self.socket_path}"
        return f"brak pluginu na {self.socket_path}"

    def operator_task_command(self) -> str:
        return f"koru ide doctor --ide {self.ide} --fix --gc-sockets"
