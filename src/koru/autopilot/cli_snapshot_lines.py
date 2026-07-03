"""Pure DSL line-rendering helpers for ``koru autopilot snapshot``."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

from koru.autonomy.decision_trace import human_skip_reason, load_recent_decisions
from koru.ide_adapters.bridge import evaluate_bridge


def _dsl_quote(value: Any, *, max_len: int = 240) -> str:
    text = str(value or "").strip()
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return shlex.quote(text)


def _bridge_line(*, ide: str, socket_path: str, project: Path, plugins: list) -> str:
    bridge = evaluate_bridge(ide=ide, socket_path=socket_path, project=project, plugins=plugins)
    return " ".join([
        "#003",
        "act=bridge",
        'intent="IDE bridge readiness"',
        f"route=ide:{ide}",
        f"ok={'true' if bridge.ready else 'false'}",
        f"reason={_dsl_quote(bridge.operator_detail())}",
    ])


def _plugin_labels(plugins: list) -> list[str]:
    """Human-readable label per plugin row (ide, id, or ``?``)."""
    return [
        str(row.get("ide") or row.get("id") or "?")
        for row in plugins
        if isinstance(row, dict)
    ]


def _daemon_detail(daemon: dict[str, Any], info: dict[str, Any]) -> str:
    """pid/version/sha detail string for the daemon health line."""
    return (
        f"pid={daemon.get('pid') or info.get('daemon_pid') or '-'} "
        f"version={daemon.get('version') or info.get('daemon_version') or '-'} "
        f"sha={daemon.get('git_sha') or '-'}"
    )


def _runtime_lines(
    *,
    project: Path,
    ide: str,
    socket_path: str,
    info: dict[str, Any],
) -> list[str]:
    daemon = info.get("daemon") if isinstance(info.get("daemon"), dict) else {}
    plugins = info.get("plugins") if isinstance(info.get("plugins"), list) else []
    plugin_labels = _plugin_labels(plugins)
    detail = _daemon_detail(daemon, info)
    plugin_reason = f"plugins={len(plugins)} labels={','.join(plugin_labels) or '-'}"
    lines = [
        " ".join([
            "#001",
            "act=runtime",
            'intent="daemon health"',
            f"route=socket:{socket_path}",
            "ok=true",
            f"detail={_dsl_quote(detail)}",
        ]),
        " ".join([
            "#002",
            "act=runtime",
            'intent="plugin session"',
            f"route=ide:{ide}",
            f"ok={'true' if plugins else 'false'}",
            f"reason={_dsl_quote(plugin_reason)}",
        ]),
    ]
    lines.append(_bridge_line(ide=ide, socket_path=socket_path, project=project, plugins=plugins))
    return lines


def _decision_lines(project: Path, *, limit: int) -> list[str]:
    history = load_recent_decisions(project, limit=max(1, limit))
    if not history:
        return [
            '#004 act=decision intent="autonomous cycle" route=telemetry ok=false '
            'reason="no decisions recorded yet"'
        ]
    item = history[-1]
    skip_code = str(item.get("skip_code") or "unknown")
    because = str(item.get("skip_because") or human_skip_reason(skip_code))
    return [
        " ".join(
            [
                "#004",
                "act=decision",
                'intent="last autonomous cycle"',
                "route=telemetry",
                f"ok={'true' if skip_code == 'ok' else 'false'}",
                f"cycle={int(item.get('cycle') or 0)}",
                f"code={skip_code}",
                f"observed={_dsl_quote(item.get('observed'))}",
                f"decided={_dsl_quote(item.get('decided'))}",
                f"because={_dsl_quote(because)}",
            ]
        )
    ]


def _observe_path_line(project: Path, *, ticket: str | None, limit: int) -> list[str]:
    try:
        from koru.cqrs.event_store import JsonlEventStore
        from koru.observability_dsl import OBSERVABILITY_CONTEXT, render_observability_path
        from koru.observability_writer import observability_event_store_path
    except ImportError:
        return []

    store = JsonlEventStore(observability_event_store_path(project))
    events = [
        event
        for event in store.all_events(context=OBSERVABILITY_CONTEXT)
        if not ticket or str((event.payload or {}).get("ticket") or "") == ticket
    ]
    if limit > 0:
        events = events[-limit:]
    if not events:
        return []
    path = render_observability_path(events).replace("\n", " | ")
    return [f"#005 act=obs intent=\"semantic path\" route=observe ok=true path={_dsl_quote(path, max_len=500)}"]


def _filter_drive_lines(raw_lines: list) -> list[str]:
    """Non-empty drive DSL lines, excluding operator-analysis acts."""
    skip_acts = {"diagnose", "next", "replay", "validate"}
    return [
        str(line)
        for line in raw_lines
        if str(line).strip()
        and not any(
            token.startswith(f"act={act}")
            for act in skip_acts
            for token in str(line).split()
        )
    ]


def _drive_dsl_lines(project: Path, *, limit: int) -> list[str]:
    path = project / ".planfile" / ".koru" / "dsl_recent.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [
            '#006 act=drive intent="last plugin drive trace" route=dsl_recent ok=false '
            'reason="no drive DSL recorded yet"'
        ]
    raw_lines = payload.get("lines") if isinstance(payload, dict) else None
    if not isinstance(raw_lines, list) or not raw_lines:
        return [
            '#006 act=drive intent="last plugin drive trace" route=dsl_recent ok=false '
            'reason="drive DSL file is empty"'
        ]
    lines = _filter_drive_lines(raw_lines)
    if limit > 0:
        lines = lines[-limit:]
    out = ['#006 act=drive intent="last plugin drive trace" route=dsl_recent ok=true']
    out.extend(lines)
    return out


def _live_desktop_probe(project: Path) -> dict[str, Any] | None:
    try:
        from env2llm.probes.desktop import collect_desktop_probe
    except ImportError:
        return None
    try:
        payload = collect_desktop_probe(project_dir=project)
    except (OSError, RuntimeError):
        return None
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload if isinstance(payload, dict) else None


def _env2llm_error_line(error: str) -> str:
    return " ".join([
        "#007", "act=env2llm", 'intent="desktop registry"',
        "route=registry", "ok=false", f"reason={_dsl_quote(error)}",
    ])


def _calibration_line(idx: int, row: dict) -> str:
    return " ".join([
        f"#007.{idx + 1}", "act=env2llm", 'intent="IDE chat anchor"',
        f"route=calibration:{row.get('ide')}",
        f"chat_x={row.get('chat_x')}",
        f"chat_y={row.get('chat_y')}",
        f"display_id={row.get('display_id') or '-'}",
    ])


def _env2llm_unavailable_error(payload: Any) -> str:
    """Error text when neither registry nor live probe produced a desktop."""
    return (
        payload.get("error")
        if isinstance(payload, dict) and payload.get("error")
        else "desktop unavailable (pip install env2llm; ENV2LLM_DESKTOP_PROBE=1 env2llm . --probe-desktop)"
    )


def _env2llm_desktop_lines(route: str, desktop: dict[str, Any]) -> list[str]:
    """Summary line plus up to three IDE calibration lines for the desktop."""
    pointer = desktop.get("pointer") if isinstance(desktop.get("pointer"), dict) else {}
    calibrations = desktop.get("ide_calibrations") if isinstance(desktop.get("ide_calibrations"), list) else []
    lines = [
        " ".join([
            "#007", "act=env2llm", 'intent="desktop registry"',
            f"route={route}", "ok=true",
            f"displays={len(desktop.get('displays') or [])}",
            f"pointer_display={pointer.get('display_id') or '-'}",
            f"pointer_x={pointer.get('x') or '-'}",
            f"pointer_y={pointer.get('y') or '-'}",
            f"ide_calibrations={len(calibrations)}",
        ])
    ]
    for idx, row in enumerate(calibrations[:3]):
        if isinstance(row, dict):
            lines.append(_calibration_line(idx, row))
    return lines


def _env2llm_lines(project: Path) -> list[str]:
    try:
        from koruapi.env2llm_registry import env2llm_get_desktop
    except ImportError:
        return []
    payload = env2llm_get_desktop(project_dir=str(project), refresh=True)
    desktop = payload.get("desktop") if isinstance(payload, dict) else None
    route = "registry"
    if not isinstance(desktop, dict):
        desktop = _live_desktop_probe(project)
        route = "probe"
    if not isinstance(desktop, dict):
        return [_env2llm_error_line(_env2llm_unavailable_error(payload))]
    return _env2llm_desktop_lines(route, desktop)


def _skip_code_from_decision_lines(decision_lines: list[str]) -> str:
    """Extract ``code=`` token from the first decision line, or ``unknown``."""
    skip_code = "unknown"
    if decision_lines:
        for token in decision_lines[0].split():
            if token.startswith("code="):
                skip_code = token.split("=", 1)[1]
    return skip_code
