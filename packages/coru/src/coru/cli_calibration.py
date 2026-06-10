"""Calibration preflight, testql scenarios, and plugin probe drives for ``coru calibration``."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

_PLUGIN_CALIBRATION_IDES = frozenset({"cursor", "windsurf", "vscode", "vscodium", "antigravity"})

_CALIBRATION_DESKTOP_WINDOW_TITLES: dict[str, tuple[str, ...]] = {
    "cursor": ("Cursor", "koru", "cursor"),
    "vscode": ("Visual Studio Code", "Code", "koru"),
    "vscodium": ("VSCodium", "koru"),
    "windsurf": ("Windsurf", "koru"),
    "antigravity": ("Antigravity", "koru"),
}

_CALIBRATION_DRIVE_TIMEOUT_S = 45.0


def _calibration_desktop_focus_titles(ide: str, *, workspace_name: str | None = None) -> tuple[str, ...]:
    titles = list(_CALIBRATION_DESKTOP_WINDOW_TITLES.get(ide, (ide.title(),)))
    if workspace_name:
        ws = workspace_name.strip()
        if ws and ws not in titles:
            titles.append(ws)
    return tuple(dict.fromkeys(titles))


def _desktop_capture_enabled() -> bool:
    return os.environ.get("CORU_CALIBRATION_DESKTOP_CAPTURE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _calibration_desktop_template_path(ide: str, root: Path) -> Path | None:
    scenarios = root / "testql-scenarios"
    for name in (f"{ide}-desktop-calibration.oql", f"{ide}-desktop.oql"):
        candidate = scenarios / name
        if candidate.is_file():
            return candidate
    return None


def _append_desktop_focus_lines(lines: list[str], focus_titles: Sequence[str]) -> None:
    for title in focus_titles:
        lines.append(f'DESKTOP_FOCUS "{title}"')
        lines.append(f'DESKTOP_ASSERT_WINDOW "{title}"')


def _materialize_calibration_desktop_oql(
    *,
    ide: str,
    root: Path,
    focus_titles: Sequence[str],
) -> tuple[Path, str]:
    """Write a runnable desktop OQL scenario; return (path, source label)."""
    out_dir = root / ".planfile" / ".koru"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"calibration-{ide}-desktop.oql"
    capture = out_dir / f"calibration-{ide}-desktop.png"
    template = _calibration_desktop_template_path(ide, root)
    if template is not None:
        body = template.read_text(encoding="utf-8").rstrip()
        primary = focus_titles[0] if focus_titles else ide.title()
        body = re.sub(
            r'^SET window_title ".*"$',
            f'SET window_title "{primary}"',
            body,
            count=1,
            flags=re.MULTILINE,
        )
        body = re.sub(
            r'^SET capture_path ".*"$',
            f'SET capture_path "{capture}"',
            body,
            count=1,
            flags=re.MULTILINE,
        )
        extra: list[str] = []
        seen = {primary.casefold()}
        for title in focus_titles[1:]:
            if title.casefold() in seen:
                continue
            seen.add(title.casefold())
            extra.extend([f'DESKTOP_FOCUS "{title}"', f'DESKTOP_ASSERT_WINDOW "{title}"'])
        lines = [body, *extra]
        if _desktop_capture_enabled():
            lines.append('DESKTOP_CAPTURE "${capture_path}"')
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out_path, f"template:{template.relative_to(root)}"

    lines = [
        f"# generated for coru calibration ide={ide}",
        f'SET capture_path "{capture}"',
        "DESKTOP_LIST",
    ]
    _append_desktop_focus_lines(lines, focus_titles)
    if _desktop_capture_enabled():
        lines.append('DESKTOP_CAPTURE "${capture_path}"')
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path, "generated"


def _write_calibration_desktop_oql(
    *,
    ide: str,
    root: Path,
    focus_titles: Sequence[str],
) -> Path:
    path, _source = _materialize_calibration_desktop_oql(
        ide=ide,
        root=root,
        focus_titles=focus_titles,
    )
    return path


def _write_calibration_bridge_testql(
    *,
    ide: str,
    instance: str,
    root: Path,
) -> Path:
    out_dir = root / ".planfile" / ".koru"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"calibration-{ide}-bridge.testql.toon.yaml"
    lines = [
        f"# generated for coru calibration ide={ide} instance={instance}",
        "# TYPE: cli",
        "CONFIG[3]{key, value}:",
        f"  instance, {instance}",
        f"  ide, {ide}",
        "  timeout_ms, 15000",
        'SHELL "KORU_AUTOPILOT_INSTANCE=${instance} koru autopilot status --format json" ${timeout_ms}',
        "ASSERT_EXIT_CODE 0",
        'SHELL "KORU_AUTOPILOT_INSTANCE=${instance} koru autopilot manage --ide ${ide} --format json" ${timeout_ms}',
        "ASSERT_EXIT_CODE 0",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _testql_run_scenario(scenario_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "testql",
        "run",
        str(scenario_path),
        "--output",
        "json",
        "--quiet",
    ]
    if dry_run:
        cmd.append("--dry-run")
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=45.0,
            close_fds=True,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "testql run timed out"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    raw = (proc.stdout or "").strip()
    if not raw:
        err = (proc.stderr or "").strip()
        return {"ok": False, "error": err or f"testql exited {proc.returncode} with empty stdout"}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": "testql JSON output parse failed", "stdout": raw[:500]}
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    if not isinstance(payload, dict):
        return {"ok": False, "error": "unexpected testql JSON shape"}
    payload.setdefault("ok", proc.returncode == 0)
    payload["scenario"] = str(scenario_path)
    return payload


def _testql_run_oql(oql_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    return _testql_run_scenario(oql_path, dry_run=dry_run)


def _format_calibration_desktop_report(
    result: dict[str, Any] | None,
    *,
    ide: str,
    focus_titles: Sequence[str],
    oql_path: Path | None = None,
    oql_source: str | None = None,
) -> list[str]:
    lines = ["[coru] calibration: desktop preflight (testql DESKTOP_*)"]
    if result is None:
        lines.append("  status=skipped (testql not importable)")
        return lines
    if oql_path is not None:
        lines.append(f"  scenario={oql_path}")
    if oql_source:
        lines.append(f"  source={oql_source}")
    if result.get("error"):
        lines.append(f"  status=error issue={result['error']}")
        lines.append(
            "  hint=install testql: pip install testql; optional host tools: wmctrl xdotool wtype"
        )
        return lines
    ok = bool(result.get("ok"))
    passed = result.get("passed")
    failed = result.get("failed")
    lines.append(f"  ok={ok} passed={passed} failed={failed}")
    lines.append(f"  focus_candidates={','.join(focus_titles)}")
    if not ok:
        lines.append(
            "  hint=bring the IDE window to the foreground; on Wayland wmctrl may not "
            "see Electron titles — plugin drive will still run"
        )
    return lines


def _format_calibration_bridge_report(
    result: dict[str, Any] | None,
    *,
    ide: str,
    instance: str,
    scenario_path: Path | None = None,
) -> list[str]:
    lines = ["[coru] calibration: bridge preflight (testql SHELL status/manage)"]
    if result is None:
        lines.append("  status=skipped (testql not importable)")
        return lines
    if scenario_path is not None:
        lines.append(f"  scenario={scenario_path}")
    lines.append(f"  lane={ide}/{instance}")
    if result.get("error"):
        lines.append(f"  status=error issue={result['error']}")
        return lines
    ok = bool(result.get("ok"))
    lines.append(f"  ok={ok} passed={result.get('passed')} failed={result.get('failed')}")
    if not ok:
        errors = result.get("errors") or []
        if errors:
            lines.append(f"  issue={errors[0]}")
        lines.append(
            "  hint=start daemon and connect plugin: "
            "KORU_AUTOPILOT_INSTANCE=<instance> koru autopilot daemon; "
            "koru: Connect autopilot daemon"
        )
    return lines


def _run_calibration_desktop_preflight(
    ide: str,
    *,
    skip: bool = False,
) -> tuple[bool, list[str]]:
    from coru.cli import _repo_root

    if skip or os.environ.get("CORU_CALIBRATION_SKIP_DESKTOP", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return True, ["[coru] calibration: desktop preflight skipped"]
    try:
        import testql  # noqa: F401
    except ImportError:
        return True, _format_calibration_desktop_report(None, ide=ide, focus_titles=())

    root = _repo_root() or Path.cwd()
    workspace = root.name
    focus_titles = _calibration_desktop_focus_titles(ide, workspace_name=workspace)
    oql_path, oql_source = _materialize_calibration_desktop_oql(
        ide=ide,
        root=root,
        focus_titles=focus_titles,
    )
    result = _testql_run_oql(oql_path, dry_run=False)
    lines = _format_calibration_desktop_report(
        result,
        ide=ide,
        focus_titles=focus_titles,
        oql_path=oql_path,
        oql_source=oql_source,
    )
    return True, lines


def _run_calibration_bridge_preflight(
    ide: str,
    instance: str,
    *,
    skip: bool = False,
) -> tuple[bool, list[str]]:
    from coru.cli import _repo_root

    if skip or os.environ.get("CORU_CALIBRATION_SKIP_BRIDGE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return True, ["[coru] calibration: bridge preflight skipped"]
    try:
        import testql  # noqa: F401
    except ImportError:
        return True, _format_calibration_bridge_report(None, ide=ide, instance=instance)

    root = _repo_root() or Path.cwd()
    scenario_path = _write_calibration_bridge_testql(ide=ide, instance=instance, root=root)
    result = _testql_run_scenario(scenario_path, dry_run=False)
    lines = _format_calibration_bridge_report(
        result,
        ide=ide,
        instance=instance,
        scenario_path=scenario_path,
    )
    return True, lines


def _parse_drive_json_from_stdout(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _lane_drive_capture(
    ide: str,
    instance: str,
    prompt: str,
    *,
    require_plugin: bool = True,
    timeout: float = _CALIBRATION_DRIVE_TIMEOUT_S,
) -> tuple[int, dict[str, Any] | None]:
    from coru.cli import _koru_exec_argv, _lane_subprocess_env

    koru_exec = _koru_exec_argv()
    if koru_exec is None:
        print("error: koru is not available; run 'coru ensure --install'", file=sys.stderr)
        return 127, None
    cmd = [*koru_exec, "autopilot", "drive", "--ide", ide]
    if require_plugin:
        cmd.append("--require-plugin")
    cmd.append(prompt)
    env = _lane_subprocess_env(ide, instance)
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            check=False,
            env=env,
            timeout=timeout,
            close_fds=True,
        )
    except subprocess.TimeoutExpired:
        print(
            f"[coru] calibration: drive timed out after {timeout:.0f}s",
            file=sys.stderr,
        )
        return 1, None
    except Exception:
        return 1, None
    raw = proc.stdout or ""
    if raw.strip():
        sys.stdout.write(raw if raw.endswith("\n") else raw + "\n")
        sys.stdout.flush()
    return proc.returncode, _parse_drive_json_from_stdout(raw)


def _probe_report_verification(drive: dict[str, Any]) -> str:
    return str(drive.get("verification") or drive.get("intent_validator") or "").strip()


def _probe_report_header_lines(drive: dict[str, Any]) -> list[str]:
    verification = _probe_report_verification(drive)
    return [
        "[coru] calibration: probe result",
        f"  ok={drive.get('ok')}",
        f"  verification={verification or '-'}",
        f"  winning_focus_open={drive.get('winning_focus_open') or '-'}",
        f"  winning_paste={drive.get('winning_paste') or '-'}",
        f"  winning_submit={drive.get('winning_submit') or '-'}",
    ]


def _probe_report_failure_reason(drive: dict[str, Any]) -> str:
    return str(
        drive.get("submit_failure_reason")
        or drive.get("intent_reason")
        or drive.get("message")
        or drive.get("reason")
        or "probe drive failed"
    )


def _probe_report_unverified_hint(verification: str) -> str | None:
    if verification not in {"submit_unverified", "intent_not_validated"}:
        return None
    return (
        "  hint=focus chat input, press Send manually, or run "
        "Command Palette → koru: Calibrate chat probe ladder"
    )


def _format_calibration_probe_report(drive: dict[str, Any] | None) -> tuple[bool, list[str]]:
    """Summarize a plugin probe drive for ``coru calibration``."""
    if not drive:
        return False, ["[coru] calibration: probe — no drive ack (daemon/plugin may be down)"]

    verification = _probe_report_verification(drive)
    lines = _probe_report_header_lines(drive)
    if (
        drive.get("ok") is True
        and verification not in {"submit_unverified", "intent_not_validated"}
        and drive.get("winning_focus_open")
        and drive.get("winning_paste")
    ):
        return True, lines

    if drive.get("ok") is True and verification not in {"submit_unverified", "intent_not_validated"}:
        lines.append("  issue=missing winning focus/paste proof")
        return False, lines

    lines.append(f"  issue={_probe_report_failure_reason(drive)}")
    hint = _probe_report_unverified_hint(verification)
    if hint:
        lines.append(hint)
    return False, lines


def _resolve_calibration_lane(
    ide: str,
    instance: str,
    *,
    explicit_ide: str | None,
) -> tuple[str, str]:
    """Prefer the integrated terminal IDE for calibration unless explicitly overridden."""
    from coru.cli import (
        _infer_default_instance,
        _print_terminal_context,
        _terminal_shell_context,
    )

    _print_terminal_context()
    term_ide, _term_source, integrated = _terminal_shell_context()
    if explicit_ide:
        if integrated and term_ide and term_ide != ide:
            print(
                f"[coru] calibration: explicit ide={ide} while integrated terminal "
                f"is {term_ide} — using explicit lane",
                file=sys.stderr,
            )
        return ide, instance
    if integrated and term_ide and term_ide in _PLUGIN_CALIBRATION_IDES and ide != term_ide:
        corrected_instance = _infer_default_instance(ide=term_ide)
        print(
            f"[coru] calibration: lane corrected {ide}/{instance} -> "
            f"{term_ide}/{corrected_instance} (integrated terminal)",
            file=sys.stderr,
        )
        return term_ide, corrected_instance
    if ide not in _PLUGIN_CALIBRATION_IDES or (
        term_ide and term_ide != ide and not integrated
    ):
        print(
            f"[coru] calibration: targeting ide={ide}/{instance}. "
            f"For Cursor use: `coru calibration cursor` or "
            f"`KORU_AUTOPILOT_INSTANCE=cursor-main coru calibration`",
            file=sys.stderr,
        )
    return ide, instance


def _lane_calibration(
    ide: str,
    instance: str,
    *,
    probe_prompt: str = "probe test",
    skip_fix: bool = False,
    skip_desktop: bool = False,
    skip_bridge: bool = False,
) -> int:
    """Preflight bridge, align socket, and run an end-to-end plugin probe drive."""
    from coru.cli import (
        _diagnose_lane,
        _koru_autopilot_env_payload,
        _lane_status_payload,
        _lane_status_raw,
        _print_troubleshooting_log_locations,
        _run_koru_lane,
        _run_lane_repair,
        _target_plugin_rows,
    )

    print(f"[coru] calibration ide={ide} instance={instance}")
    _print_troubleshooting_log_locations(ide, instance)

    rc = _diagnose_lane(ide, instance, skip_ensure=False)
    if not skip_fix:
        print("[coru] calibration: aligning workspace socket (koru ide doctor --fix --gc-sockets)...")
        fix_rc = _run_koru_lane(
            ide,
            instance,
            ["ide", "doctor", "--ide", ide, "--fix", "--gc-sockets"],
        )
        if fix_rc == 2:
            print("[coru] calibration: ide doctor failed (invalid lane/adapter)", file=sys.stderr)
            return fix_rc
        if fix_rc != 0:
            print(
                "[coru] calibration: bridge not ready after socket fix "
                "(daemon/plugin may still need reconnect — continuing checks)",
                file=sys.stderr,
            )
        rc = _lane_status_raw(ide, instance)

    if rc != 0:
        print(
            "[coru] calibration: preflight failed — start daemon and connect plugin first",
            file=sys.stderr,
        )
        return rc

    if ide not in _PLUGIN_CALIBRATION_IDES:
        print(
            f"[coru] calibration: ide={ide} uses keyboard/OS-injector path; "
            f"run: koru autopilot calibrate --ide {ide}",
            file=sys.stderr,
        )
        return 0

    plugins = _target_plugin_rows(_lane_status_payload(ide, instance), ide=ide)
    if not plugins:
        print(
            "[coru] calibration: plugin not connected — "
            "Command Palette → koru: Connect autopilot daemon",
            file=sys.stderr,
        )
        return 1

    from coru.cli import (
        _lane_drive_capture,
        _run_calibration_bridge_preflight,
        _run_calibration_desktop_preflight,
    )

    _, desktop_lines = _run_calibration_desktop_preflight(ide, skip=skip_desktop)
    for line in desktop_lines:
        print(line)

    _, bridge_lines = _run_calibration_bridge_preflight(ide, instance, skip=skip_bridge)
    for line in bridge_lines:
        print(line)

    print(f"[coru] calibration: probe drive (prompt={probe_prompt!r})...")
    probe_rc, drive = _lane_drive_capture(
        ide,
        instance,
        probe_prompt,
        require_plugin=True,
    )
    ok, lines = _format_calibration_probe_report(drive)
    for line in lines:
        print(line)
    if ok:
        print("[coru] calibration: PASS — focus/paste/submit path verified")
        return 0

    if drive:
        payload = _koru_autopilot_env_payload(ide, instance) or {}
        payload = {**payload, "drive": drive}
        _run_lane_repair(ide, instance, payload=payload, trigger="coru.calibration.probe")
    print("[coru] calibration: FAIL — fix issues above before `coru auto`", file=sys.stderr)
    return probe_rc or 1


def _register_calibration_command(sub: Any) -> None:
    from coru.cli import _add_lane_identifiers

    p_calibration = sub.add_parser(
        "calibration",
        help="preflight bridge, align socket, and run plugin probe drive (works in integrated terminal)",
    )
    _add_lane_identifiers(p_calibration)
    p_calibration.add_argument(
        "--probe-prompt",
        default="probe test",
        help="prompt sent via koru autopilot drive --require-plugin",
    )
    p_calibration.add_argument(
        "--skip-fix",
        action="store_true",
        help="skip koru ide doctor --fix --gc-sockets before probe",
    )
    p_calibration.add_argument(
        "--skip-desktop",
        action="store_true",
        help="skip testql DESKTOP_* window preflight before plugin probe",
    )
    p_calibration.add_argument(
        "--skip-bridge",
        action="store_true",
        help="skip testql SHELL status/manage preflight before plugin probe",
    )


__all__ = [
    "_CALIBRATION_DRIVE_TIMEOUT_S",
    "_PLUGIN_CALIBRATION_IDES",
    "_calibration_desktop_focus_titles",
    "_format_calibration_bridge_report",
    "_format_calibration_desktop_report",
    "_format_calibration_probe_report",
    "_lane_calibration",
    "_lane_drive_capture",
    "_materialize_calibration_desktop_oql",
    "_parse_drive_json_from_stdout",
    "_register_calibration_command",
    "_resolve_calibration_lane",
    "_run_calibration_bridge_preflight",
    "_run_calibration_desktop_preflight",
    "_write_calibration_bridge_testql",
    "_write_calibration_desktop_oql",
]
