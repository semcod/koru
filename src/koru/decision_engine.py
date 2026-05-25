"""Central decision engine — OS × IDE × LLM axes combined.

Higher layers (autonomous loop, operator pipeline, ide_reload) ask this
module for typed decisions instead of scattering ``if ide == cursor``
/ ``if WAYLAND_DISPLAY`` / ``if focus in msg`` across the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from koru.environment_profile import (
    EnvironmentProfile,
    resolve_environment_profile,
)
from koruos import OsStrategy, resolve_active_os_strategy
from korullm import (
    DriveFailureAssessment,
    LlmStrategy,
    resolve_active_llm_strategy,
)
from koruide.ides import get_strategy as get_ide_strategy

_VSCODE_FAMILY_IDES = frozenset({"antigravity", "cursor", "vscode", "vscodium", "windsurf"})

ReloadMethod = Literal["command_palette", "reuse_window", "none"]


@dataclass(frozen=True)
class ReloadDecision:
    """Whether and how to reload the IDE after a VSIX install."""

    should_attempt: bool
    method: ReloadMethod
    reason: str
    stale: bool = False
    installed_version: str | None = None
    live_version: str | None = None


@dataclass(frozen=True)
class FocusDecision:
    """Outcome of attempting to focus the IDE window."""

    ok: bool
    method: str = ""
    detail: str = ""
    os_strategy_id: str = ""


@dataclass(frozen=True)
class DriveRetryDecision:
    """What the autonomous loop should do after a failed drive."""

    assessment: DriveFailureAssessment
    should_retry: bool
    should_warn: str | None = None
    sleep_seconds: float = 0.0


class EnvironmentDecisionEngine:
    """Resolve environment-scoped decisions from the three strategy axes."""

    def __init__(
        self,
        project: Path,
        *,
        ide: str | None = "auto",
        profile: EnvironmentProfile | None = None,
        os_strategy: OsStrategy | None = None,
        llm_strategy: LlmStrategy | None = None,
    ) -> None:
        self.project = project
        self.profile = profile or resolve_environment_profile(project, ide=ide)
        self.os_strategy = os_strategy or resolve_active_os_strategy()
        self.llm_strategy = llm_strategy or resolve_active_llm_strategy()
        self.ide_id = self.profile.ide.id
        self._ide_strategy = get_ide_strategy(self.ide_id)

    @property
    def decision_key(self) -> str:
        return self.profile.decision_key

    def focus_ide_window(self) -> FocusDecision:
        """Focus the IDE using the OS strategy + IDE-axis guard."""
        hints = self._window_name_hints()
        outcome = self.os_strategy.focus_window(hints)
        if outcome.ok and outcome.method == "integrated_terminal":
            if not self._ide_accepts_integrated_terminal():
                return FocusDecision(
                    ok=False,
                    detail="integrated_terminal not accepted for this IDE family",
                    os_strategy_id=self.os_strategy.id,
                )
        return FocusDecision(
            ok=outcome.ok,
            method=outcome.method,
            detail=outcome.detail,
            os_strategy_id=self.os_strategy.id,
        )

    def assess_drive_failure(
        self,
        reply: dict[str, Any],
        *,
        attempt: int,
        max_attempts: int,
    ) -> DriveRetryDecision:
        """Map a failed plugin drive reply to retry/stop behaviour."""
        if self._submit_retry_is_known_unsafe(reply):
            assessment = DriveFailureAssessment(
                kind="stop",
                failure_signature=self.llm_strategy.failure_signature(reply),
                detail="vscodium_submit_unverified_not_retryable",
            )
            return DriveRetryDecision(assessment=assessment, should_retry=False)

        assessment = self.llm_strategy.assess_drive_failure(
            reply,
            attempt=attempt,
            max_attempts=max_attempts,
        )
        kind = assessment.kind
        if kind in {"stop", "stop_manual_focus"}:
            return DriveRetryDecision(
                assessment=assessment,
                should_retry=False,
                should_warn=assessment.warn_banner,
            )
        if kind == "skip_cooldown":
            return DriveRetryDecision(
                assessment=assessment,
                should_retry=False,
            )
        return DriveRetryDecision(
            assessment=assessment,
            should_retry=True,
            should_warn=assessment.warn_banner,
            sleep_seconds=assessment.sleep_seconds,
        )

    def _submit_retry_is_known_unsafe(self, reply: dict[str, Any]) -> bool:
        """Avoid paste/submit loops for IDEs that cannot confirm Send reliably."""
        if self.ide_id != "vscodium":
            return False
        verification = str(reply.get("verification") or "").strip().lower()
        if verification in {"submit_unverified", "submit_failed"}:
            return True
        if reply.get("submitted") is False and (
            reply.get("attempted_submit")
            or reply.get("winning_paste")
            or reply.get("submit_failure_reason")
        ):
            return True
        return "submit could not be verified" in str(reply.get("message") or "").lower()

    def detect_stale_extension_host(
        self,
        client: Any,
    ) -> ReloadDecision:
        """Compare on-disk VSIX version vs live plugin version."""
        if self._ide_strategy is None:
            return ReloadDecision(
                should_attempt=False,
                method="none",
                reason="unknown IDE",
            )
        try:
            from koruide.plugin_installer import installed_extension_version_for_ide
        except ImportError:
            return ReloadDecision(
                should_attempt=False,
                method="none",
                reason="plugin_installer unavailable",
            )
        installed = installed_extension_version_for_ide(self.ide_id)
        live = _live_plugin_version(client, self.ide_id)
        if not installed or not live:
            return ReloadDecision(
                should_attempt=False,
                method="none",
                reason="version unknown",
                installed_version=installed,
                live_version=live,
            )
        stale = installed != live
        return ReloadDecision(
            should_attempt=stale,
            method="command_palette" if stale else "none",
            reason="stale_extension_host" if stale else "versions_match",
            stale=stale,
            installed_version=installed,
            live_version=live,
        )

    def reload_capability_detail(self) -> str:
        caps = self.os_strategy.capabilities()
        return (
            f"os={self.os_strategy.id}; keyboard={caps.keyboard_tool or '-'}; "
            f"focus={','.join(caps.focus_methods) or '-'}"
        )

    def _window_name_hints(self) -> tuple[str, ...]:
        if self._ide_strategy is not None:
            return self._ide_strategy.window_name_hints()
        return (self.ide_id,)

    def _ide_accepts_integrated_terminal(self) -> bool:
        return self.ide_id in _VSCODE_FAMILY_IDES


def _live_plugin_version(client: Any, ide: str) -> str | None:
    status_fn = getattr(client, "status", None)
    if not callable(status_fn):
        return None
    try:
        status = status_fn()
    except (OSError, TimeoutError, RuntimeError):
        return None
    plugins = status.get("plugins") if isinstance(status, dict) else None
    if not isinstance(plugins, list):
        return None
    ide_lower = (ide or "").lower()
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        if str(plugin.get("ide") or "").lower() == ide_lower:
            version = plugin.get("version")
            return str(version) if version else None
    return None


def build_decision_engine(
    project: Path,
    *,
    ide: str | None = "auto",
) -> EnvironmentDecisionEngine:
    """Factory used by the autonomous loop and operator pipeline."""
    return EnvironmentDecisionEngine(project, ide=ide)


__all__ = [
    "DriveRetryDecision",
    "EnvironmentDecisionEngine",
    "FocusDecision",
    "ReloadDecision",
    "ReloadMethod",
    "build_decision_engine",
]
