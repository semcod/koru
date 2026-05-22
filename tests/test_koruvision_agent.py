from __future__ import annotations

from unittest import mock

from koruvision.agent import (
    MIN_CAPTURE_INTERVAL_SECONDS,
    normalize_capture_interval,
    run_capture_loop,
)


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


def test_capture_interval_never_goes_below_30_seconds() -> None:
    assert normalize_capture_interval(0.01) == MIN_CAPTURE_INTERVAL_SECONDS

    with mock.patch("koruvision.agent.capture_once") as capture:
        capture.return_value = mock.Mock(frame_id="abc", payload=b"x", captured_at="t")
        with mock.patch("koruvision.agent.time.sleep") as sleep:
            count = run_capture_loop(
                interval_seconds=0.01,
                on_frame=lambda _frame: None,
                max_frames=2,
            )

    assert count == 2
    sleep.assert_called_once_with(MIN_CAPTURE_INTERVAL_SECONDS)


def test_run_capture_loop_multi_monitor_uses_capture_all() -> None:
    from unittest.mock import MagicMock

    frame_a = MagicMock(frame_id="m0")
    frame_b = MagicMock(frame_id="m1")
    seen: list[str] = []

    with mock.patch("koruvision.agent.capture_all_once") as capture_all:
        capture_all.return_value = [frame_a, frame_b]
        with mock.patch("koruvision.agent.time.sleep"):
            count = run_capture_loop(
                interval_seconds=60,
                monitor_id=None,
                on_frame=lambda f: seen.append(f.frame_id),
                max_frames=4,
            )
    assert count == 4
    assert seen == ["m0", "m1", "m0", "m1"]
