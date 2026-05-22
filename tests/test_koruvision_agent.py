from __future__ import annotations

from unittest import mock

from koruvision.agent import run_capture_loop


def test_run_capture_loop_respects_max_frames() -> None:
    frames: list[int] = []

    with mock.patch("koruvision.agent.capture_once") as capture:
        capture.return_value = mock.Mock(frame_id="abc", payload=b"x", captured_at="t")
        with mock.patch("koruvision.agent.time.sleep"):
            count = run_capture_loop(
                interval_seconds=60,
                on_frame=lambda frame: frames.append(len(frame.payload)),
                max_frames=3,
            )
    assert count == 3
    assert frames == [1, 1, 1]


def test_run_capture_loop_retries_after_capture_error() -> None:
    frames: list[str] = []

    with mock.patch("koruvision.agent.capture_once") as capture:
        capture.side_effect = [RuntimeError("display unavailable"), mock.Mock(frame_id="abc")]
        with mock.patch("koruvision.agent.time.sleep") as sleep:
            count = run_capture_loop(
                interval_seconds=60,
                on_frame=lambda frame: frames.append(frame.frame_id),
                max_frames=1,
            )

    assert count == 1
    assert frames == ["abc"]
    sleep.assert_called_once_with(60)
