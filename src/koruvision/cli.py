"""CLI for ``koru vision`` (capture + agent loop)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from koru.configurator import load_project_config
from koruvision.agent import capture_once, run_capture_loop


def _vision_interval(project: Path, override: float | None) -> float:
    if override is not None:
        return override
    saved = load_project_config(project)
    vision = saved.get("vision") if isinstance(saved.get("vision"), dict) else {}
    return float(vision.get("interval_seconds") or 60)


def build_vision_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="koru vision", description="Capture monitors for observation mesh.")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root (.koru/config.json).")
    sub = parser.add_subparsers(dest="command", required=True)

    once = sub.add_parser("capture", help="Capture one monitor frame.")
    once.add_argument("--monitor", type=int, default=0, help="Monitor index.")

    agent = sub.add_parser("agent", help="Run periodic capture loop.")
    agent.add_argument("--monitor", type=int, default=0, help="Monitor index.")
    agent.add_argument("--interval", type=float, default=None, help="Seconds between captures.")
    agent.add_argument("--max-frames", type=int, default=None, help="Stop after N frames (for tests).")
    return parser


def vision_main(argv: list[str] | None = None) -> int:
    args = build_vision_parser().parse_args(argv)
    try:
        if args.command == "capture":
            frame = capture_once(args.monitor)
            print(
                f"koru vision: frame={frame.frame_id} monitor={frame.monitor_id} "
                f"{frame.width}x{frame.height} bytes={len(frame.payload)}"
            )
            return 0
        interval = _vision_interval(args.project, args.interval)

        def _print_frame(frame) -> None:
            print(
                f"koru vision agent: {frame.captured_at} frame={frame.frame_id} "
                f"bytes={len(frame.payload)}"
            )

        count = run_capture_loop(
            interval_seconds=interval,
            monitor_id=args.monitor,
            on_frame=_print_frame,
            max_frames=args.max_frames,
        )
        print(f"koru vision agent: captured {count} frame(s)", file=sys.stderr)
    except (RuntimeError, ValueError) as exc:
        print(f"koru vision: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0
    return 0
