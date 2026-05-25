"""Base adapter for VS Code API–compatible editors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from koru.ide_adapters.base import ActivationReport, Hypothesis, Remediation, SettingsReport
from koru.ide_adapters import shared


@dataclass
class VSCodeFamilyAdapter:
    ide_id: str
    label: str
    requires_trusted_publisher: bool = True

    @property
    def extension_id(self) -> str:
        return shared.extension_id_for_ide(self.ide_id)

    def diagnose_activation(self) -> ActivationReport:
        hypotheses: list[Hypothesis] = []
        if shared.extension_disabled(self.ide_id):
            hypotheses.append(
                Hypothesis(
                    id=f"{self.ide_id}.extension.disabled",
                    confidence=0.95,
                    evidence=f"Rozszerzenie {self.extension_id} jest na liście disabled",
                    remediation=Remediation(
                        kind="manual",
                        summary=f"Extensions → włącz {self.extension_id}",
                    ),
                ),
            )
        if self.requires_trusted_publisher and shared.publisher_trusted(self.ide_id) is False:
            hyp = shared.untrusted_publisher_hypothesis(self.ide_id)
            if hyp is not None:
                hypotheses.append(hyp)
        hyp = shared.inactive_extension_hypothesis(self.ide_id)
        if hyp is not None:
            hypotheses.append(hyp)
        if not shared.extension_listed_in_extensions_json(self.ide_id):
            hypotheses.append(
                Hypothesis(
                    id=f"{self.ide_id}.extension.not_installed",
                    confidence=0.7,
                    evidence=f"Brak {self.extension_id} w extensions.json",
                    remediation=Remediation(
                        kind="command",
                        summary="Zainstaluj wtyczkę",
                        command=f"koru autopilot install-plugin --ide {self.ide_id}",
                    ),
                ),
            )
        active = shared.extension_activated_in_exthost(self.ide_id)
        installed = shared.extension_listed_in_extensions_json(self.ide_id)
        return ActivationReport(
            extension_installed=installed if installed else None,
            extension_active=active,
            extension_id=self.extension_id,
            hypotheses=tuple(hypotheses),
        )

    def analyze_settings(
        self,
        *,
        project: Path | None,
        expected_socket: str,
    ) -> SettingsReport:
        return shared.analyze_socket_settings(
            ide=self.ide_id,
            project=project,
            expected_socket=expected_socket,
        )

    def collect_hypotheses(
        self,
        *,
        project: Path | None,
        expected_socket: str,
        plugins_connected: bool,
    ) -> list[Hypothesis]:
        if plugins_connected:
            return []
        out: list[Hypothesis] = []
        activation = self.diagnose_activation()
        out.extend(activation.hypotheses)
        settings = self.analyze_settings(project=project, expected_socket=expected_socket)
        hyp = shared.settings_mismatch_hypothesis(settings)
        if hyp is not None:
            out.append(hyp)
        if not out:
            out.append(
                Hypothesis(
                    id=f"{self.ide_id}.plugin.not_connected",
                    confidence=0.5,
                    evidence=f"Plugin nie połączony z daemonem na {expected_socket}",
                    remediation=Remediation(
                        kind="manual",
                        summary=(
                            "Command Palette → Developer: Reload Window, potem "
                            "koru: Connect autopilot daemon "
                            f"(socket {expected_socket})"
                        ),
                    ),
                ),
            )
        return sorted(out, key=lambda h: h.confidence, reverse=True)

    def apply_safe_fixes(
        self,
        *,
        project: Path | None,
        expected_socket: str,
        fix: bool,
        ide_running: bool,
    ) -> list[str]:
        if not fix:
            return []
        applied: list[str] = []
        settings = self.analyze_settings(project=project, expected_socket=expected_socket)
        if settings.mismatch and project is not None:
            path = shared.fix_workspace_socket(
                project=project,
                ide=self.ide_id,
                expected_socket=expected_socket,
            )
            if path is not None:
                applied.append(f"workspace socketPath → {expected_socket} ({path})")
        if self.requires_trusted_publisher and shared.publisher_trusted(self.ide_id) is False:
            if shared.add_trusted_publisher(self.ide_id):
                applied.append(
                    f"extensions.trustedPublishers += {shared.PUBLISHER_ID} "
                    f"(wymagany Developer: Reload Window w {self.label})"
                )
        return applied
