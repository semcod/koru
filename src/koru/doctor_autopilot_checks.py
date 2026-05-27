"""Autopilot environment, socket, and manager checks for ``koru --doctor``."""

from __future__ import annotations

import os
from pathlib import Path

from koru.autonomy.environment import probe_socket_health
from koru.autopilot.ide import (
    detect_running_ides,
    detect_terminal_host_ide_id,
    normalize_ide_id,
)
from koru.autopilot.install_manager import collect_install_manager_report
from koru.doctor_constants import FAIL, PASS, SKIP, WARN
from koruide.socket import default_socket_path


def _running_autopilot_ide_ids() -> list[str]:
    seen: list[str] = []
    for item in detect_running_ides():
        ide = normalize_ide_id(getattr(item, "id", ""))
        if ide and ide not in seen:
            seen.append(ide)
    return seen


def _lane_matrix_bits(selected: str) -> list[str]:
    running = _running_autopilot_ide_ids()
    if len(running) < 2:
        return []
    summaries: list[str] = []
    for ide in running:
        try:
            report = collect_install_manager_report(ide=ide)
        except Exception:
            summaries.append(f"{ide}:error")
            continue
        daemon = report.daemon if isinstance(report.daemon, dict) else {}
        plugin = report.plugin if isinstance(report.plugin, dict) else {}
        daemon_state = "running" if daemon.get("running") else "stopped"
        plugin_state = "connected" if plugin.get("connected") else "disconnected"
        marker = "*" if ide == selected else ""
        summaries.append(f"{ide}{marker}:{daemon_state}/{plugin_state}")
    return [
        f"running_ides={','.join(running)}",
        "explicit_env_required_when_multiple=true",
        f"lane_matrix={','.join(summaries)}",
    ]


def _selected_autopilot_ide(*, include_terminal_hint: bool = True) -> str | None:
    raw_ide = os.environ.get("KORU_AUTOPILOT_IDE")
    raw_instance = os.environ.get("KORU_AUTOPILOT_INSTANCE")
    selected = normalize_ide_id(raw_ide) or normalize_ide_id(raw_instance)
    if selected or not include_terminal_hint:
        return selected
    return normalize_ide_id(detect_terminal_host_ide_id())


def _has_autopilot_selection() -> bool:
    return bool(
        os.environ.get("KORU_AUTOPILOT_IDE")
        or os.environ.get("KORU_AUTOPILOT_INSTANCE")
        or os.environ.get("KORU_AUTOPILOT_SOCKET")
        or _selected_autopilot_ide(include_terminal_hint=True)
    )


def _resolve_autopilot_socket_for_doctor() -> Path:
    selected = _selected_autopilot_ide()
    if selected and not os.environ.get("KORU_AUTOPILOT_SOCKET"):
        previous = os.environ.get("KORU_AUTOPILOT_INSTANCE")
        try:
            os.environ["KORU_AUTOPILOT_INSTANCE"] = selected
            return default_socket_path()
        finally:
            if previous is None:
                os.environ.pop("KORU_AUTOPILOT_INSTANCE", None)
            else:
                os.environ["KORU_AUTOPILOT_INSTANCE"] = previous
    return default_socket_path()


def _autopilot_env_snapshot() -> dict[str, str]:
    return {
        "instance": (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip(),
        "ide": (os.environ.get("KORU_AUTOPILOT_IDE") or "").strip(),
        "socket_env": (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip(),
        "terminal": detect_terminal_host_ide_id() or "-",
        "session": os.environ.get("XDG_SESSION_TYPE") or "-",
        "runtime": os.environ.get("XDG_RUNTIME_DIR") or "-",
    }


def _autopilot_env_detail_bits(values: dict[str, str]) -> list[str]:
    return [
        f"instance={values['instance'] or '-'}",
        f"ide={values['ide'] or '-'}",
        f"socket_env={values['socket_env'] or '-'}",
        f"terminal_hint={values['terminal']}",
        f"session={values['session']}",
        f"runtime={values['runtime']}",
    ]


def _autopilot_env_status(values: dict[str, str]) -> tuple[str, list[str]]:
    normalized_instance = normalize_ide_id(values["instance"])
    normalized_ide = normalize_ide_id(values["ide"])
    if normalized_instance and normalized_ide and normalized_instance != normalized_ide:
        return WARN, ["instance_ide_mismatch=true"]
    if not _selected_autopilot_ide(include_terminal_hint=True):
        return SKIP, ["autopilot_env=unset"]
    if not (values["instance"] or values["ide"] or values["socket_env"]):
        selected = _selected_autopilot_ide(include_terminal_hint=True) or "auto"
        return WARN, ["autopilot_env=unset", "using_terminal_hint=true", *_lane_matrix_bits(selected)]
    return PASS, []


def _check_autopilot_env(_project: Path) -> tuple[str, str]:
    values = _autopilot_env_snapshot()
    status, extra_bits = _autopilot_env_status(values)
    return status, "; ".join(_autopilot_env_detail_bits(values) + extra_bits)


def _check_ide_runtime_presence(_project: Path) -> tuple[str, str]:
    selected = _selected_autopilot_ide()
    running = detect_running_ides()
    ids = [item.id for item in running]
    detail = f"selected={selected or '-'}; running={', '.join(ids) or '-'}"
    if not selected:
        return SKIP, detail
    if selected not in ids:
        return WARN, detail + "; selected_ide_not_running=true"
    return PASS, detail


def _check_autopilot_socket(_project: Path) -> tuple[str, str]:
    if not _has_autopilot_selection():
        return SKIP, "autopilot env unset"
    path = _resolve_autopilot_socket_for_doctor()
    health = probe_socket_health(path)
    detail = (
        f"path={health.path}; exists={health.exists}; "
        f"listening={health.listening}; stale={health.stale}"
    )
    if health.healthy:
        return PASS, detail
    if health.stale:
        return WARN, detail + "; restart daemon or remove stale socket"
    return WARN, detail + "; daemon not listening yet"


def _check_autopilot_manage(_project: Path) -> tuple[str, str]:
    if not _has_autopilot_selection():
        return SKIP, "autopilot env unset"
    selected = _selected_autopilot_ide() or "auto"
    report = collect_install_manager_report(
        ide=selected,
        socket_path=_resolve_autopilot_socket_for_doctor(),
    )
    issue_rows = [issue.to_dict() for issue in report.issues]
    severities = {str(row.get("severity")) for row in issue_rows}
    issue_codes = ", ".join(str(row.get("code")) for row in issue_rows) or "-"
    plugin = report.plugin
    daemon_running = bool(report.daemon.get("running"))
    detail = (
        f"ide={plugin.get('ide')}; daemon={'running' if daemon_running else 'stopped'}; "
        f"socket={report.socket}; connected={plugin.get('connected')}; "
        f"connected_version={plugin.get('connected_version') or '-'}; "
        f"installed={plugin.get('installed_version') or '-'}; "
        f"expected={plugin.get('expected_version') or '-'}; issues={issue_codes}"
    )
    if "error" in severities:
        return FAIL, detail
    if severities:
        return WARN, detail
    return PASS, detail


def _check_autopilot_runtime_status(_project: Path) -> tuple[str, str]:
    if not _has_autopilot_selection():
        return SKIP, "autopilot env unset"
    selected = _selected_autopilot_ide() or "auto"
    report = collect_install_manager_report(
        ide=selected,
        socket_path=_resolve_autopilot_socket_for_doctor(),
    )
    daemon = _report_mapping(report.daemon)
    plugin = _report_mapping(report.plugin)
    plugins = _daemon_plugin_rows(daemon)
    issue_rows = _install_issue_rows(report)
    detail_bits = _autopilot_runtime_detail_bits(
        selected=selected,
        report=report,
        daemon=daemon,
        plugin=plugin,
        plugins=plugins,
    )
    status = _autopilot_runtime_check_status(daemon, plugin, issue_rows)
    issue_codes = _install_issue_codes(issue_rows)
    if status == FAIL:
        return FAIL, "; ".join(detail_bits + [f"issues={issue_codes}"])
    if status == WARN:
        return WARN, "; ".join(detail_bits + [f"issues={issue_codes}"])
    return PASS, "; ".join(detail_bits + ["runtime_status=healthy"])


def _report_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _daemon_plugin_rows(daemon: dict[str, object]) -> list[dict[str, object]]:
    plugins = daemon.get("plugins")
    if not isinstance(plugins, list):
        return []
    return [row for row in plugins if isinstance(row, dict)]


def _install_issue_rows(report: object) -> list[dict[str, object]]:
    return [issue.to_dict() for issue in getattr(report, "issues", [])]


def _autopilot_runtime_detail_bits(
    *,
    selected: str,
    report: object,
    daemon: dict[str, object],
    plugin: dict[str, object],
    plugins: list[dict[str, object]],
) -> list[str]:
    plugin_labels = [str(row.get("ide") or row.get("id") or "?") for row in plugins]
    detail_bits = [
        f"ide={plugin.get('ide') or selected}",
        f"daemon={'running' if daemon.get('running') else 'stopped'}",
        f"socket={getattr(report, 'socket', '-')}",
        f"plugins={len(plugins)}",
        f"plugin_labels={','.join(plugin_labels) or '-'}",
        f"connected={plugin.get('connected')}",
        f"connected_version={plugin.get('connected_version') or '-'}",
        f"connected_build={plugin.get('connected_build_sha') or '-'}",
        f"installed_version={plugin.get('installed_version') or '-'}",
        f"expected_version={plugin.get('expected_version') or '-'}",
        f"expected_build={plugin.get('expected_build_sha') or '-'}",
    ]
    detail_bits.extend(_lane_matrix_bits(selected))
    return detail_bits


def _autopilot_runtime_check_status(
    daemon: dict[str, object],
    plugin: dict[str, object],
    issue_rows: list[dict[str, object]],
) -> str:
    severities = {str(row.get("severity")) for row in issue_rows}
    if "error" in severities:
        return FAIL
    if severities or not daemon.get("running"):
        return WARN
    if plugin.get("supported") is not False and not plugin.get("connected"):
        return WARN
    return PASS


def _install_issue_codes(issue_rows: list[dict[str, object]]) -> str:
    return ",".join(str(row.get("code")) for row in issue_rows) or "-"
