"""Tests for autopilot drive retry hygiene (dedup + bounded attempts).

The autonomous loop used to call :func:`AutopilotClient.drive` up to 5
times back-to-back with a 5 s sleep between attempts even when every reply
carried the same failure reason. That wasted 20–25 s per cycle and spammed
the operator with identical red banners. The drive retry helper now
collapses consecutive identical failures and honours
``KORU_AUTOPILOT_DRIVE_MAX_RETRIES`` for the absolute upper bound.
"""

from __future__ import annotations

import os
import unittest
from typing import Any
from unittest import mock

from koru.autonomous_cycle_drive_retry import (
    _drive_failure_signature,
    _execute_autopilot_drive,
    _max_drive_retries,
)


class FailureSignatureTests(unittest.TestCase):
    def test_signature_collapses_message_casing_and_whitespace(self) -> None:
        a = {"message": "Chat input is not focused/open", "verification": "Focus_Failed"}
        b = {"message": "chat input is not focused/open", "verification": "focus_failed"}
        self.assertEqual(_drive_failure_signature(a), _drive_failure_signature(b))

    def test_signature_differs_when_reason_changes(self) -> None:
        a = {"message": "chat input is not focused/open"}
        b = {"message": "submit could not be verified"}
        self.assertNotEqual(_drive_failure_signature(a), _drive_failure_signature(b))


class MaxRetriesEnvTests(unittest.TestCase):
    def test_default_is_three(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KORU_AUTOPILOT_DRIVE_MAX_RETRIES", None)
            self.assertEqual(_max_drive_retries(), 3)

    def test_env_override_is_clamped(self) -> None:
        with mock.patch.dict(os.environ, {"KORU_AUTOPILOT_DRIVE_MAX_RETRIES": "0"}):
            self.assertEqual(_max_drive_retries(), 1)
        with mock.patch.dict(os.environ, {"KORU_AUTOPILOT_DRIVE_MAX_RETRIES": "99"}):
            self.assertEqual(_max_drive_retries(), 10)
        with mock.patch.dict(os.environ, {"KORU_AUTOPILOT_DRIVE_MAX_RETRIES": "junk"}):
            self.assertEqual(_max_drive_retries(), 3)


class ExecuteDriveDedupTests(unittest.TestCase):
    """Drive failures with identical signatures should not loop forever."""

    def _run_execute(
        self,
        replies: list[dict[str, Any]],
        *,
        env: dict[str, str] | None = None,
    ) -> tuple[int, list[str]]:
        """Drive ``replies`` through ``_execute_autopilot_drive`` and observe calls."""
        from koru.autonomy.state import AutoloopState
        from koru.queue import QueueLoopResult

        call_count = {"n": 0}
        captured_messages: list[str] = []

        class FakeClient:
            def drive(self, *_a: Any, **_kw: Any) -> dict[str, Any]:
                index = call_count["n"]
                call_count["n"] += 1
                if index < len(replies):
                    return replies[index]
                return replies[-1]

            def status(self) -> dict[str, Any]:
                return {"plugins": [{"ide": "cursor", "version": "0.1.71"}]}

        def fake_hp(msg: str) -> None:
            captured_messages.append(str(msg))

        state = AutoloopState()
        queue_result = QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=["TEST-1"],
            last_status="waiting_input",
            last_message="please continue",
            last_ticket_id="TEST-1",
        )

        with (
            mock.patch(
                "koru.autonomous_cycle_drive_retry._resolve_autopilot_drive_decision",
                return_value=(
                    mock.Mock(
                        skip=False,
                        kind="ticket_prompt",
                        prompt="hello",
                        skip_reason=None,
                    ),
                    None,
                ),
            ),
            mock.patch(
                "koru.autonomous_cycle_drive_retry._resolve_drive_plugin_requirement",
                return_value=True,
            ),
            mock.patch("koru.autonomous_drive_retry_policy.time.sleep", lambda *_a: None),
            mock.patch.dict(os.environ, env or {}, clear=False),
        ):
            _execute_autopilot_drive(
                project=mock.Mock(),
                state=state,
                queue_result=queue_result,
                client=FakeClient(),
                autopilot_ide="cursor",
                drive_prompt="hello",
                submit=True,
                autopilot_action="drive",
                _hp=fake_hp,
            )
        return call_count["n"], captured_messages

    def test_identical_failures_break_after_second_attempt(self) -> None:
        focus_fail = {
            "ok": False,
            "message": "chat input is not focused/open",
            "verification": "focus_failed",
        }
        attempts, messages = self._run_execute(
            [focus_fail, focus_fail, focus_fail, focus_fail],
        )
        self.assertEqual(attempts, 2, "should break after seeing identical signature twice")
        self.assertTrue(
            any("identical failure repeated" in m for m in messages),
            "should log the dedup reason",
        )

    def test_changing_failures_keep_retrying(self) -> None:
        first = {"ok": False, "message": "chat input is not focused/open"}
        second = {"ok": False, "message": "submit could not be verified"}
        ok_reply = {"ok": True, "backend": "plugin", "verification": "submit_ok"}
        attempts, _ = self._run_execute([first, second, ok_reply])
        self.assertEqual(attempts, 3)

    def test_env_override_caps_retries(self) -> None:
        first = {"ok": False, "message": "submit could not be verified A"}
        second = {"ok": False, "message": "submit could not be verified B"}
        third = {"ok": False, "message": "submit could not be verified C"}
        fourth = {"ok": False, "message": "submit could not be verified D"}
        attempts, _ = self._run_execute(
            [first, second, third, fourth],
            env={"KORU_AUTOPILOT_DRIVE_MAX_RETRIES": "2"},
        )
        self.assertEqual(attempts, 2)


if __name__ == "__main__":
    unittest.main()
