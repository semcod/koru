"""Tests for the environment decision engine."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from koru.decision_engine import build_decision_engine
from korullm.strategies.ide_chat import IdeChatStrategy
from koruos.strategies.wayland_linux import WaylandLinuxStrategy


class DecisionEngineTests(unittest.TestCase):
    def test_build_engine_composes_axes(self) -> None:
        project = Path("/tmp/koru-decision-engine-test")
        with (
            mock.patch.dict("os.environ", {"KORU_AUTOPILOT_INSTANCE": "cursor"}, clear=False),
            mock.patch(
                "koru.environment_profile.detect_running_ides",
                return_value=[],
            ),
            mock.patch(
                "koru.environment_profile.detect_terminal_host_ide_id",
                return_value=None,
            ),
        ):
            engine = build_decision_engine(project, ide="cursor")
        self.assertEqual(engine.ide_id, "cursor")
        self.assertIn("ide=cursor", engine.decision_key)

    def test_assess_drive_failure_delegates_to_llm_strategy(self) -> None:
        project = Path("/tmp/koru-decision-engine-test")
        llm = IdeChatStrategy()
        os_strategy = WaylandLinuxStrategy()
        with (
            mock.patch(
                "koru.decision_engine.resolve_environment_profile",
            ) as mock_profile,
            mock.patch(
                "koru.decision_engine.resolve_active_os_strategy",
                return_value=os_strategy,
            ),
            mock.patch(
                "koru.decision_engine.resolve_active_llm_strategy",
                return_value=llm,
            ),
            mock.patch(
                "koru.decision_engine.get_ide_strategy",
                return_value=None,
            ),
        ):
            mock_profile.return_value = mock.Mock(
                ide=mock.Mock(id="cursor"),
                decision_key="test",
            )
            from koru.decision_engine import EnvironmentDecisionEngine

            engine = EnvironmentDecisionEngine(
                project,
                ide="cursor",
                profile=mock_profile.return_value,
                os_strategy=os_strategy,
                llm_strategy=llm,
            )
            decision = engine.assess_drive_failure(
                {"message": "chat input is not focused"},
                attempt=0,
                max_attempts=3,
            )
        self.assertTrue(decision.should_retry)
        self.assertEqual(decision.should_warn, "focus")

    def test_vscodium_submit_unverified_does_not_retry(self) -> None:
        project = Path("/tmp/koru-decision-engine-test")
        llm = IdeChatStrategy()
        os_strategy = WaylandLinuxStrategy()
        with (
            mock.patch("koru.decision_engine.resolve_environment_profile") as mock_profile,
            mock.patch(
                "koru.decision_engine.resolve_active_os_strategy",
                return_value=os_strategy,
            ),
            mock.patch(
                "koru.decision_engine.resolve_active_llm_strategy",
                return_value=llm,
            ),
            mock.patch("koru.decision_engine.get_ide_strategy", return_value=None),
        ):
            mock_profile.return_value = mock.Mock(
                ide=mock.Mock(id="vscodium"),
                decision_key="test",
            )
            from koru.decision_engine import EnvironmentDecisionEngine

            engine = EnvironmentDecisionEngine(
                project,
                ide="vscodium",
                profile=mock_profile.return_value,
                os_strategy=os_strategy,
                llm_strategy=llm,
            )
            decision = engine.assess_drive_failure(
                {
                    "verification": "submit_unverified",
                    "winning_paste": "host-clipboard:wl-copy+xdotool key ctrl+v",
                    "attempted_submit": "vscodium-host-key-noop",
                },
                attempt=0,
                max_attempts=3,
            )
        self.assertFalse(decision.should_retry)
        self.assertEqual(decision.assessment.detail, "vscodium_submit_unverified_not_retryable")

    def test_focus_ide_window_accepts_integrated_terminal_for_cursor(self) -> None:
        project = Path("/tmp/koru-decision-engine-test")
        os_strategy = WaylandLinuxStrategy()
        focus_outcome = mock.Mock(
            ok=True,
            method="integrated_terminal",
            detail="ok",
        )
        with (
            mock.patch(
                "koru.decision_engine.resolve_environment_profile",
            ) as mock_profile,
            mock.patch(
                "koru.decision_engine.resolve_active_os_strategy",
                return_value=os_strategy,
            ),
            mock.patch(
                "koru.decision_engine.resolve_active_llm_strategy",
                return_value=IdeChatStrategy(),
            ),
            mock.patch.object(
                WaylandLinuxStrategy,
                "focus_window",
                return_value=focus_outcome,
            ),
        ):
            mock_profile.return_value = mock.Mock(
                ide=mock.Mock(id="cursor"),
                decision_key="test",
            )
            from koru.decision_engine import EnvironmentDecisionEngine

            engine = EnvironmentDecisionEngine(
                project,
                ide="cursor",
                profile=mock_profile.return_value,
                os_strategy=os_strategy,
                llm_strategy=IdeChatStrategy(),
            )
            focus = engine.focus_ide_window()
        self.assertTrue(focus.ok)
        self.assertEqual(focus.method, "integrated_terminal")


if __name__ == "__main__":
    unittest.main()
