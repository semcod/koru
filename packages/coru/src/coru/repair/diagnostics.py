"""Autodiagnostics: collect :class:`RepairProblem` rows from status, manage, drive, readiness."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from coru.repair.domain import RepairProblem

_EXTENSION_LAYOUT: dict[str, tuple[str, str]] = {
    "cursor": (".cursor/extensions", "semcod.koru-autopilot-cursor"),
    "vscode": (".vscode/extensions", "semcod.koru-autopilot-vscode"),
    "vscodium": (".vscode-oss/extensions", "semcod.koru-autopilot-vscodium"),
    "windsurf": (".windsurf/extensions", "semcod.koru-autopilot-windsurf"),
    "antigravity": (".antigravity/extensions", "semcod.koru-autopilot-antigravity"),
}

_TOXIC_FOCUS_TOKENS = ("workbench.panel.chat", "composer.openAsPane", "aichat.newchataction")
_TOXIC_PASTE_TOKENS = (
    "terminal.paste",
    "editor.action.clipboardPasteAction",
    "startcomposerprompt",
)


def _read_package_build_sha(package_json: Path) -> str | None:
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    build_info = payload.get("koruAutopilotBuild") if isinstance(payload, dict) else None
    if isinstance(build_info, dict) and isinstance(build_info.get("sha"), str):
        return build_info["sha"] or None
    return None


def _installed_extension_dir(ide: str) -> Path | None:
    layout = _EXTENSION_LAYOUT.get(ide)
    if layout is None:
        return None
    rel_root, ext_prefix = layout
    ext_root = Path.home() / rel_root
    if not ext_root.is_dir():
        return None
    matches = sorted(
        ext_root.glob(f"{ext_prefix}-*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def _plugin_row_for_ide(status: Mapping[str, Any] | None, ide: str) -> dict[str, Any] | None:
    if not status:
        return None
    plugins = status.get("plugins")
    if not isinstance(plugins, list):
        return None
    for row in plugins:
        if isinstance(row, dict) and str(row.get("ide") or "").strip().lower() == ide:
            return row
    return None


def _dedupe_problems(problems: Sequence[RepairProblem]) -> list[RepairProblem]:
    seen: set[str] = set()
    out: list[RepairProblem] = []
    for problem in problems:
        key = f"{problem.code}|{problem.message}"
        if key in seen:
            continue
        seen.add(key)
        out.append(problem)
    return out


def dedupe_problems(problems: Sequence[RepairProblem]) -> list[RepairProblem]:
    return _dedupe_problems(problems)


def _problem_from_manage_issue(raw: Any) -> RepairProblem | None:
    if not isinstance(raw, Mapping):
        return None
    code = str(raw.get("code") or "").strip()
    if not code:
        return None
    return RepairProblem(
        code=code,
        severity=str(raw.get("severity") or "error"),  # type: ignore[arg-type]
        message=str(raw.get("message") or code),
        fix_hint=str(raw.get("fix") or "") or None,
        context={"source": "manage_report"},
    )


def _collect_manage_issue_problems(report: Mapping[str, Any]) -> list[RepairProblem]:
    problems: list[RepairProblem] = []
    for raw in report.get("issues") or ():
        if problem := _problem_from_manage_issue(raw):
            problems.append(problem)
    return problems


def _install_plugin_failure_code(message: str) -> str:
    lower = message.lower()
    if "sandbox" in lower or "zygote" in lower:
        return "install_plugin_cli_sandbox"
    return "install_plugin_failed"


def _problem_from_manage_action(action: Any) -> RepairProblem | None:
    if not isinstance(action, Mapping):
        return None
    name = str(action.get("action") or action.get("name") or "").strip()
    result = action.get("result") if isinstance(action.get("result"), Mapping) else {}
    status = str(result.get("status") or action.get("install_plugin") or "").strip().lower()
    if name != "install_plugin" or status not in {"failed", "error"}:
        return None

    message = str(result.get("message") or "").strip()
    return RepairProblem(
        code=_install_plugin_failure_code(message),
        severity="error",
        message=message or "koru autopilot plugin install failed",
        fix_hint="Install VSIX manually or use coru repair manual_vsix_unpack",
        context={"source": "manage_report.actions", "installer_message": message},
    )


def _collect_manage_action_problems(report: Mapping[str, Any]) -> list[RepairProblem]:
    problems: list[RepairProblem] = []
    for action in report.get("actions") or ():
        if problem := _problem_from_manage_action(action):
            problems.append(problem)
    return problems


def collect_problems_from_manage_report(report: Mapping[str, Any]) -> list[RepairProblem]:
    problems = _collect_manage_issue_problems(report)

    plugin = report.get("plugin") if isinstance(report.get("plugin"), dict) else {}
    problems.extend(_collect_plugin_alignment_problems(plugin, source="manage_report.plugin"))
    problems.extend(_collect_manage_action_problems(report))
    return _dedupe_problems(problems)


def _missing_status_payload_problems(
    ide: str,
    *,
    daemon_running: bool,
) -> list[RepairProblem]:
    if not daemon_running:
        return []
    return [
        RepairProblem(
            code="plugin_not_connected",
            severity="error",
            message=f"No autopilot status payload for ide={ide}",
            fix_hint="Start daemon and connect plugin",
            context={"source": "status"},
        )
    ]


def _rejected_plugin_problems(status: Mapping[str, Any], ide: str) -> list[RepairProblem]:
    rejected = status.get("rejected_plugins")
    if not isinstance(rejected, list):
        return []
    problems: list[RepairProblem] = []
    for row in rejected:
        if not isinstance(row, dict):
            continue
        if str(row.get("ide") or "").strip().lower() != ide:
            continue
        reason = str(row.get("reason") or row.get("message") or "rejected by daemon").strip()
        problems.append(
            RepairProblem(
                code="plugin_rejected_by_daemon",
                severity="error",
                message=f"Plugin rejected: {reason}",
                fix_hint="Reload Window or strict handshake cycle",
                context={"source": "status.rejected_plugins", "rejection": row},
            )
        )
    return problems


def _plugin_not_connected_problem(*, ide: str, source: str) -> RepairProblem:
    return RepairProblem(
        code="plugin_not_connected",
        severity="error",
        message=f"No connected plugin for ide={ide}",
        fix_hint="koru: Connect autopilot daemon",
        context={"source": source},
    )


def _disk_build_for_ide(ide: str) -> str | None:
    installed_dir = _installed_extension_dir(ide)
    if installed_dir is None:
        return None
    return _read_package_build_sha(installed_dir / "package.json")


def _plugin_build_sha_mismatch_problems(
    *,
    ide: str,
    connected_build: str,
    expected_build: str,
    source: str,
) -> list[RepairProblem]:
    disk_build = _disk_build_for_ide(ide)
    context = {
        "source": source,
        "connected_build": connected_build,
        "expected_build": expected_build,
        "disk_build": disk_build,
    }
    if disk_build == expected_build:
        return [
            RepairProblem(
                code="plugin_extension_stale_in_memory",
                severity="error",
                message=(
                    f"Plugin build in IDE memory ({connected_build}) differs from repo "
                    f"({expected_build}); extension on disk is current"
                ),
                fix_hint="Developer: Reload Window, then koru: Connect autopilot daemon",
                context=context,
            )
        ]
    return [
        RepairProblem(
            code="plugin_extension_stale_on_disk",
            severity="error",
            message=(
                f"Plugin build mismatch: connected={connected_build or '-'} "
                f"disk={disk_build or '-'} expected={expected_build}"
            ),
            fix_hint="Install current VSIX into IDE extensions directory",
            context=context,
        )
    ]


def collect_problems_from_status(
    status: Mapping[str, Any] | None,
    *,
    ide: str,
    expected_build: str | None = None,
    daemon_running: bool = True,
) -> list[RepairProblem]:
    if not status:
        return _missing_status_payload_problems(ide, daemon_running=daemon_running)

    problems = _rejected_plugin_problems(status, ide)
    row = _plugin_row_for_ide(status, ide)
    if row is None:
        problems.append(_plugin_not_connected_problem(ide=ide, source="status.plugins"))
        return _dedupe_problems(problems)

    connected_build = str(row.get("buildSha") or "").strip()
    if expected_build and connected_build and connected_build != expected_build:
        problems.extend(
            _plugin_build_sha_mismatch_problems(
                ide=ide,
                connected_build=connected_build,
                expected_build=expected_build,
                source="status.build",
            )
        )
    return _dedupe_problems(problems)


def _submit_unverified_problem(drive: Mapping[str, Any]) -> RepairProblem | None:
    verification = str(drive.get("verification") or drive.get("intent_validator") or "").strip()
    if drive.get("ok") is not False:
        return None
    if verification not in {"submit_unverified", "intent_not_validated"}:
        return None
    reason = str(
        drive.get("submit_failure_reason")
        or drive.get("intent_reason")
        or drive.get("message")
        or "submit could not be verified"
    )
    return RepairProblem(
        code="submit_unverified",
        severity="error",
        message=reason,
        fix_hint=str(drive.get("operator_hint") or "") or None,
        context={
            "source": "drive.ack",
            "verification": verification,
            "winning_focus_open": drive.get("winning_focus_open"),
            "winning_paste": drive.get("winning_paste"),
            "winning_submit": drive.get("winning_submit"),
        },
    )


def _drive_intent_unverified_problem(
    drive: Mapping[str, Any],
    problems: Sequence[RepairProblem],
) -> RepairProblem | None:
    intent_status = str(drive.get("intent_status") or "").strip().lower()
    if drive.get("ok") is not False or intent_status != "unverified":
        return None
    if any(problem.code == "submit_unverified" for problem in problems):
        return None
    return RepairProblem(
        code="drive_intent_unverified",
        severity="error",
        message=str(
            drive.get("intent_reason")
            or drive.get("message")
            or "drive intent unverified"
        ),
        context={"source": "drive.ack", "intent": drive.get("intent")},
    )


def _focus_risk_problem(drive: Mapping[str, Any]) -> RepairProblem | None:
    focus = str(drive.get("winning_focus_open") or "").lower()
    for token in _TOXIC_FOCUS_TOKENS:
        if token.lower() in focus:
            return RepairProblem(
                code="chat_focus_toggle_risk",
                severity="warning",
                message=f"Drive used toxic focus_open winner containing {token}",
                fix_hint="Upgrade plugin >=0.2.4 and reload IDE window",
                context={
                    "source": "drive.ack",
                    "winning_focus_open": drive.get("winning_focus_open"),
                },
            )
    return None


def _paste_risk_problem(drive: Mapping[str, Any]) -> RepairProblem | None:
    paste = str(drive.get("winning_paste") or "").lower()
    for token in _TOXIC_PASTE_TOKENS:
        if token.lower() in paste:
            return RepairProblem(
                code="terminal_paste_risk" if "terminal" in token else "probe_cache_toxic",
                severity="warning",
                message=f"Drive used toxic paste winner: {drive.get('winning_paste')}",
                fix_hint="Upgrade plugin >=0.2.4; paste should use workbench.action.chat.typeText",
                context={"source": "drive.ack", "winning_paste": drive.get("winning_paste")},
            )
    return None


def _host_key_trace_problem(drive: Mapping[str, Any]) -> RepairProblem | None:
    trace = drive.get("operation_trace")
    if not isinstance(trace, list):
        return None
    for step in trace:
        if not isinstance(step, dict):
            continue
        route = str(step.get("route") or "")
        if step.get("op") != "submit" or "host-key" not in route or step.get("ok") is not False:
            continue
        reason = str(step.get("reason") or "")
        if "pasted text" in reason.lower():
            return RepairProblem(
                code="chat_submit_host_key_failed",
                severity="warning",
                message=reason,
                context={"source": "drive.operation_trace", "route": route},
            )
    return None


def collect_problems_from_drive_result(
    drive: Mapping[str, Any] | None,
    *,
    ide: str,
) -> list[RepairProblem]:
    """Detect drive-layer failures (submit_unverified, toxic probe winners)."""
    if not drive:
        return []
    problems: list[RepairProblem] = []
    if problem := _submit_unverified_problem(drive):
        problems.append(problem)

    for problem in (
        _drive_intent_unverified_problem(drive, problems),
        _focus_risk_problem(drive),
        _paste_risk_problem(drive),
        _host_key_trace_problem(drive),
    ):
        if problem is not None:
            problems.append(problem)
    return _dedupe_problems(problems)


def collect_problems_from_console_logs(
    status: Mapping[str, Any] | None,
    *,
    ide: str,
) -> list[RepairProblem]:
    if not status:
        return []
    logs = status.get("console_logs")
    if not isinstance(logs, list):
        return []
    problems: list[RepairProblem] = []
    for entry in logs:
        if not isinstance(entry, dict):
            continue
        message = str(entry.get("message") or "")
        lower = message.lower()
        if "cache-discard" in lower and "focus_open" in lower:
            problems.append(
                RepairProblem(
                    code="probe_cache_toxic",
                    severity="warning",
                    message="Plugin discarded toxic focus_open probe cache entry",
                    fix_hint="Reload Window after upgrading plugin",
                    context={"source": "status.console_logs", "log": entry},
                )
            )
        if str(entry.get("ide") or "").strip().lower() not in {"", ide}:
            continue
    return _dedupe_problems(problems)


def _plugin_build_alignment_problem(
    *,
    ide: str,
    connected_build: str,
    expected_build: str,
    source: str,
) -> RepairProblem:
    disk_build = _disk_build_for_ide(ide) if ide else None
    code = (
        "plugin_extension_stale_in_memory"
        if disk_build == expected_build
        else "plugin_build_mismatch"
    )
    return RepairProblem(
        code=code,
        severity="error",
        message=f"Plugin build mismatch for ide={ide or '?'}",
        context={
            "source": source,
            "connected_build": connected_build,
            "expected_build": expected_build,
            "disk_build": disk_build,
        },
    )


def _plugin_version_mismatch_problem(
    *,
    ide: str,
    installed_version: str,
    expected_version: str,
    source: str,
) -> RepairProblem:
    return RepairProblem(
        code="plugin_installed_version_mismatch",
        severity="error",
        message=f"Installed plugin {installed_version} != expected {expected_version}",
        context={"source": source, "ide": ide},
    )


def _collect_plugin_alignment_problems(
    plugin: Mapping[str, Any],
    *,
    source: str,
) -> list[RepairProblem]:
    ide = str(plugin.get("ide") or "").strip().lower()
    expected_build = str(plugin.get("expected_build_sha") or "").strip()
    connected_build = str(plugin.get("connected_build_sha") or "").strip()
    installed_version = str(plugin.get("installed_version") or "").strip()
    expected_version = str(plugin.get("expected_version") or "").strip()

    problems: list[RepairProblem] = []
    if expected_build and connected_build and connected_build != expected_build:
        problems.append(
            _plugin_build_alignment_problem(
                ide=ide,
                connected_build=connected_build,
                expected_build=expected_build,
                source=source,
            )
        )
    if installed_version and expected_version and installed_version != expected_version:
        problems.append(
            _plugin_version_mismatch_problem(
                ide=ide,
                installed_version=installed_version,
                expected_version=expected_version,
                source=source,
            )
        )
    if plugin.get("connected") is False and plugin.get("supported") is not False:
        problems.append(_plugin_not_connected_problem(ide=ide, source=source))
    return problems
