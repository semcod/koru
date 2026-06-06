"""CLI actions for OS-injector profile calibration."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import gillm.injection.os_injector as oi
from koru.autopilot.ide import detect_running_ides, resolve_drive_target


def _resolve_calibration_project_dir(args: argparse.Namespace) -> Path:
    raw = getattr(args, "project", None)
    return Path(raw).resolve() if raw else Path.cwd().resolve()


def _sync_calibration_registry(
    args: argparse.Namespace,
    *,
    ide: str,
    chat_x: int,
    chat_y: int,
    config_path: Path,
) -> dict[str, object] | None:
    try:
        from koruapi.env2llm_registry import env2llm_sync_after_calibration
    except ImportError:
        return None

    project_dir = _resolve_calibration_project_dir(args)
    result = env2llm_sync_after_calibration(project_dir=str(project_dir))
    if not result.get("ok"):
        return {
            "ok": False,
            "error": result.get("error", "env2llm registry sync failed"),
        }

    calibrations = result.get("ide_calibrations") or []
    matched = next((row for row in calibrations if row.get("ide") == ide), None)
    sync_result: dict[str, object] = {
        "ok": True,
        "registry_path": result.get("registry_path"),
        "ide_calibration_count": result.get("ide_calibration_count"),
        "ide": ide,
        "chat_x": chat_x,
        "chat_y": chat_y,
        "config_path": str(config_path),
        "display_id": (matched or {}).get("display_id"),
        "display_x": (matched or {}).get("display_x"),
        "display_y": (matched or {}).get("display_y"),
    }

    # Propagate calibration validation from registry sync
    validation = result.get("validation")
    if validation:
        sync_result["validation"] = validation
        issues = validation.get("issues") or []
        errors = [i for i in issues if i.get("severity") == "error" and i.get("ide") == ide]
        warnings = [i for i in issues if i.get("severity") == "warning" and i.get("ide") == ide]
        if errors:
            import sys
            for e in errors:
                print(f"⚠ CALIBRATION ERROR [{ide}]: {e.get('message', '')}", file=sys.stderr)
        elif warnings:
            import sys
            for w in warnings:
                print(f"⚠ CALIBRATION WARNING [{ide}]: {w.get('message', '')}", file=sys.stderr)

    return sync_result


def resolve_session_ides(
    raw: str,
    *,
    detect_ides: Callable[[], list] = detect_running_ides,
) -> list[str]:
    text = (raw or "").strip()
    if not text or text == "auto":
        detected = [ide.id for ide in detect_ides()]
        out: list[str] = []
        seen: set[str] = set()
        for ide_id in detected:
            if ide_id in seen:
                continue
            seen.add(ide_id)
            out.append(ide_id)
        return out
    return [chunk.strip() for chunk in text.split(",") if chunk.strip()]


def action_calibrate(
    args: argparse.Namespace,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
    resolve_target: Callable[[str, str | None], tuple[str, str, str]] = resolve_drive_target,
) -> int:
    raw = str(args.ide).strip()
    if raw.lower() in ("", "auto"):
        _kb, ide, _reason = resolve_target("auto", None)
        if ide == "default":
            print(
                "koru autopilot calibrate: no running IDE detected; "
                "open an editor or pass --ide windsurf|vscode|cursor|…",
                file=sys.stderr,
            )
            return 2
        auto_detected = True
    else:
        ide = raw
        auto_detected = False

    delay = max(0.0, float(args.delay_seconds))
    print(f"Place mouse over IDE chat input; capturing in {delay:.1f}s...")
    sleep_fn(delay)
    try:
        x, y = oi.capture_mouse_xy()
        profile = oi.profile_from_mouse(ide, x=x, y=y)
        config_path = oi.save_profile(profile, config_path=args.config)
        payload: dict[str, object] = {
            "ok": True,
            "profile": ide,
            "chat_x": x,
            "chat_y": y,
            "config": str(config_path),
            "window_id": 0,
            "auto_detected": auto_detected,
        }
        if args.prompt:
            payload["smoke"] = oi.inject_with_profile(
                profile=profile,
                text=str(args.prompt),
                submit=True,
                dry_run=False,
            )
        registry_sync = _sync_calibration_registry(
            args,
            ide=ide,
            chat_x=x,
            chat_y=y,
            config_path=config_path,
        )
        if registry_sync is not None:
            payload["env2llm"] = registry_sync
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except oi.OsInjectorError as exc:
        print(f"koru autopilot calibrate: {exc}", file=sys.stderr)
        return 1


def capture_ide_profile(
    ide: str,
    delay: float,
    args: argparse.Namespace,
    captured: dict[tuple[int, int], list[str]],
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, object]:
    """Capture profile for a single IDE and return result row."""
    print(f"[{ide}] Place mouse over IDE chat input; capturing in {delay:.1f}s...")
    sleep_fn(delay)
    try:
        x, y = oi.capture_mouse_xy()
        profile = oi.profile_from_mouse(ide, x=x, y=y)
        config_path = oi.save_profile(profile, config_path=args.config)
        pair = (x, y)
        captured.setdefault(pair, []).append(ide)
        row: dict[str, object] = {
            "ok": True,
            "ide": ide,
            "backend": "os_injector",
            "chat_x": x,
            "chat_y": y,
            "window_id": 0,
            "config": str(config_path),
        }
        if args.prompt:
            try:
                row["smoke"] = oi.inject_with_profile(
                    profile=profile,
                    text=str(args.prompt),
                    submit=True,
                    dry_run=False,
                )
            except oi.OsInjectorError as smoke_exc:
                row["smoke"] = {"ok": False, "error": str(smoke_exc)}
                row["warning"] = "profile_saved_but_smoke_failed"
        registry_sync = _sync_calibration_registry(
            args,
            ide=ide,
            chat_x=x,
            chat_y=y,
            config_path=config_path,
        )
        if registry_sync is not None:
            row["env2llm"] = registry_sync
        return row
    except oi.OsInjectorError as exc:
        return {"ok": False, "ide": ide, "error": str(exc)}


def detect_duplicate_coordinates(
    captured: dict[tuple[int, int], list[str]],
) -> list[dict[str, object]]:
    """Detect and return list of duplicate coordinate warnings."""
    dups: list[dict[str, object]] = []
    for pair, id_list in captured.items():
        if len(id_list) > 1:
            dups.append({"chat_x": pair[0], "chat_y": pair[1], "ides": sorted(id_list)})
    return dups


def _default_session_capture_profile(
    sleep_fn: Callable[[float], None],
) -> Callable[[str, float, argparse.Namespace, dict[tuple[int, int], list[str]]], dict[str, Any]]:
    def capture_profile(
        ide: str,
        delay: float,
        ns: argparse.Namespace,
        captured: dict[tuple[int, int], list[str]],
    ) -> dict[str, Any]:
        return capture_ide_profile(
            ide,
            delay,
            ns,
            captured,
            sleep_fn=sleep_fn,
        )

    return capture_profile


def _annotate_shared_coordinate_warnings(
    targets: list[dict[str, object]],
    captured: dict[tuple[int, int], list[str]],
) -> None:
    for row in targets:
        if row.get("ok") is not True:
            continue
        pair = (int(row["chat_x"]), int(row["chat_y"]))
        peers = [ide for ide in captured.get(pair, []) if ide != row["ide"]]
        if peers:
            row["shared_with"] = sorted(peers)
            row["warning"] = "shared_coordinates_with_other_ides"


def action_session_start(
    args: argparse.Namespace,
    *,
    resolve_ides: Callable[[str], list[str]] | None = None,
    capture_profile: Callable[
        [str, float, argparse.Namespace, dict[tuple[int, int], list[str]]], dict[str, Any]
    ]
    | None = None,
    duplicate_detector: Callable[
        [dict[tuple[int, int], list[str]]], list[dict[str, object]]
    ] = detect_duplicate_coordinates,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    if resolve_ides is None:
        resolve_ides = resolve_session_ides
    if capture_profile is None:
        capture_profile = _default_session_capture_profile(sleep_fn)

    ides = resolve_ides(args.ides)
    if not ides:
        print(
            "koru autopilot session-start: no IDE ids resolved "
            "(pass --ides windsurf,cursor or run an IDE first)",
            file=sys.stderr,
        )
        return 2

    delay = max(0.0, float(args.delay_seconds))
    targets: list[dict[str, object]] = []
    ok = True
    captured: dict[tuple[int, int], list[str]] = {}

    for ide in ides:
        row = capture_profile(ide, delay, args, captured)
        if row.get("ok") is not True:
            ok = False
        targets.append(row)

    _annotate_shared_coordinate_warnings(targets, captured)

    payload: dict[str, object] = {"ok": ok, "targets": targets}
    dups = duplicate_detector(captured)
    if dups:
        payload["warnings"] = {
            "duplicate_coordinates": dups,
            "message": (
                "Multiple IDE profiles captured identical coordinates; recalibrate each IDE "
                "with its own chat input focus."
            ),
        }

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1
