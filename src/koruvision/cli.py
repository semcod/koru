"""CLI for ``koru vision`` (capture + agent loop)."""

from __future__ import annotations

import sys
from pathlib import Path

from koru.configurator import load_project_config
from koruvision.agent import capture_once, normalize_capture_interval, run_capture_loop
from koruvision.cli_parser import build_vision_parser
from koruvision.mesh import publish_vision_frame, resolve_mesh_publish


def _vision_interval(project: Path, override: float | None) -> float:
    if override is not None:
        return normalize_capture_interval(override)
    saved = load_project_config(project)
    vision = saved.get("vision") if isinstance(saved.get("vision"), dict) else {}
    return normalize_capture_interval(float(vision.get("interval_seconds") or 30))


def _mesh_publish_enabled(project: Path, explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    saved = load_project_config(project)
    mesh = saved.get("mesh") if isinstance(saved.get("mesh"), dict) else {}
    vision = saved.get("vision") if isinstance(saved.get("vision"), dict) else {}
    return bool(mesh.get("enabled")) and bool(vision.get("enabled"))


def _maybe_publish_mesh(args, frame) -> None:
    if not _mesh_publish_enabled(args.project, getattr(args, "publish_mesh", None)):
        return
    url, peer, key = resolve_mesh_publish(
        args.project,
        mesh_url=getattr(args, "mesh_url", None),
        peer_id=getattr(args, "peer_id", None),
        key_file=getattr(args, "key_file", None),
    )
    publish_vision_frame(frame, mesh_url=url, peer_from=peer, key=key)


def vision_main(argv: list[str] | None = None) -> int:
    args = build_vision_parser().parse_args(argv)
    try:
        if args.command == "capture":
            frame = capture_once(args.monitor)
            _maybe_publish_mesh(args, frame)
            print(
                f"koru vision: frame={frame.frame_id} monitor={frame.monitor_id} "
                f"{frame.width}x{frame.height} bytes={len(frame.payload)}"
            )
            return 0
        interval = _vision_interval(args.project, args.interval)

        def _on_frame(frame) -> None:
            _maybe_publish_mesh(args, frame)
            print(
                f"koru vision agent: {frame.captured_at} frame={frame.frame_id} "
                f"bytes={len(frame.payload)}"
            )

        count = run_capture_loop(
            interval_seconds=interval,
            monitor_id=args.monitor,
            on_frame=_on_frame,
            max_frames=args.max_frames,
        )
        print(f"koru vision agent: captured {count} frame(s)", file=sys.stderr)
    except (RuntimeError, ValueError) as exc:
        print(f"koru vision: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0
    return 0
