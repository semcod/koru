"""``koru autopilot snapshot`` — copy-pasteable shell OQL/DSL runtime view."""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any

from koru.autonomy.decision_trace import human_skip_reason, load_recent_decisions
from koru.autopilot.lane_context import instance_from_socket_path, resolve_lane_context
from koru.ide_adapters.bridge import evaluate_bridge, format_bridge_text
from koruide.ide import canonical_autopilot_ide_id, normalize_ide_id


def _dsl_quote(value: Any, *, max_len: int = 240) -> str:
    text = str(value or "").strip()
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return shlex.quote(text)


def _runtime_lines(
    *,
    project: Path,
    ide: str,
    socket_path: str,
    info: dict[str, Any],
) -> list[str]:
    daemon = info.get("daemon") if isinstance(info.get("daemon"), dict) else {}
    plugins = info.get("plugins") if isinstance(info.get("plugins"), list) else []
    plugin_labels = [
        str(row.get("ide") or row.get("id") or "?")
        for row in plugins
        if isinstance(row, dict)
    ]
    detail = (
        f"pid={daemon.get('pid') or info.get('daemon_pid') or '-'} "
        f"version={daemon.get('version') or info.get('daemon_version') or '-'} "
        f"sha={daemon.get('git_sha') or '-'}"
    )
    plugin_reason = f"plugins={len(plugins)} labels={','.join(plugin_labels) or '-'}"
    lines = [
        " ".join(
            [
                "#001",
                "act=runtime",
                'intent="daemon health"',
                f"route=socket:{socket_path}",
                "ok=true",
                f"detail={_dsl_quote(detail)}",
            ]
        ),
        " ".join(
            [
                "#002",
                "act=runtime",
                'intent="plugin session"',
                f"route=ide:{ide}",
                f"ok={'true' if plugins else 'false'}",
                f"reason={_dsl_quote(plugin_reason)}",
            ]
        ),
    ]
    bridge = evaluate_bridge(
        ide=ide,
        socket_path=socket_path,
        project=project,
        plugins=plugins,
    )
    lines.append(
        " ".join(
            [
                "#003",
                "act=bridge",
                'intent="IDE bridge readiness"',
                f"route=ide:{ide}",
                f"ok={'true' if bridge.ready else 'false'}",
                f"reason={_dsl_quote(bridge.operator_detail())}",
            ]
        )
    )
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
    skip_acts = {"diagnose", "next", "replay", "validate"}
    lines = [
        str(line)
        for line in raw_lines
        if str(line).strip()
        and not any(
            token.startswith(f"act={act}")
            for act in skip_acts
            for token in str(line).split()
        )
    ]
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
        error = (
            payload.get("error")
            if isinstance(payload, dict) and payload.get("error")
            else "desktop unavailable (pip install env2llm; ENV2LLM_DESKTOP_PROBE=1 env2llm . --probe-desktop)"
        )
        return [
            " ".join(
                [
                    "#007",
                    "act=env2llm",
                    'intent="desktop registry"',
                    "route=registry",
                    "ok=false",
                    f"reason={_dsl_quote(error)}",
                ]
            )
        ]
    pointer = desktop.get("pointer") if isinstance(desktop.get("pointer"), dict) else {}
    calibrations = desktop.get("ide_calibrations") if isinstance(desktop.get("ide_calibrations"), list) else []
    lines = [
        " ".join(
            [
                "#007",
                "act=env2llm",
                'intent="desktop registry"',
                f"route={route}",
                "ok=true",
                f"displays={len(desktop.get('displays') or [])}",
                f"pointer_display={pointer.get('display_id') or '-'}",
                f"pointer_x={pointer.get('x') or '-'}",
                f"pointer_y={pointer.get('y') or '-'}",
                f"ide_calibrations={len(calibrations)}",
            ]
        )
    ]
    for idx, row in enumerate(calibrations[:3]):
        if not isinstance(row, dict):
            continue
        lines.append(
            " ".join(
                [
                    f"#007.{idx + 1}",
                    "act=env2llm",
                    'intent="IDE chat anchor"',
                    f"route=calibration:{row.get('ide')}",
                    f"chat_x={row.get('chat_x')}",
                    f"chat_y={row.get('chat_y')}",
                    f"display_id={row.get('display_id') or '-'}",
                ]
            )
        )
    return lines


def _lane_shell_env(*, project: Path, ide: str, socket_path: str) -> str:
    instance = instance_from_socket_path(socket_path)
    if not instance:
        ctx = resolve_lane_context(requested_ide=ide, project=project)
        instance = ctx.instance
        socket_path = str(ctx.socket_path)
    return (
        f"KORU_AUTOPILOT_INSTANCE={instance} "
        f"KORU_AUTOPILOT_SOCKET={shlex.quote(socket_path)}"
    )


def _operator_lines(
    *,
    project: Path,
    ide: str,
    socket_path: str,
    info: dict[str, Any],
    skip_code: str,
) -> list[str]:
    plugins = info.get("plugins") if isinstance(info.get("plugins"), list) else []
    bridge = evaluate_bridge(
        ide=ide,
        socket_path=socket_path,
        project=project,
        plugins=plugins,
    )
    severity = "ok" if bridge.ready and plugins else "error"
    code = skip_code if skip_code not in ("ok", "unknown") else ("plugin_not_connected" if not plugins else "ok")
    because = bridge.operator_detail() or "daemon status plugin list is empty"
    next_step = (
        format_bridge_text(bridge, explain=False).splitlines()[-1]
        if not bridge.ready
        else "wait for IDE/LLM response or ticket state transition"
    )
    owner = "koru" if severity == "ok" else "operator"
    lane_env = _lane_shell_env(project=project, ide=ide, socket_path=socket_path)
    replay_command = f"{lane_env} koru replay 'ide connect-plugin {ide}' --explain"
    validate_command = (
        f"koru autopilot snapshot --project {shlex.quote(str(project))} --ide {ide} --include-env2llm"
    )
    return [
        " ".join(
            [
                "#900",
                "act=diagnose",
                f"severity={severity}",
                f"code={code}",
                f"because={_dsl_quote(because)}",
            ]
        ),
        " ".join(
            [
                "#901",
                "act=next",
                f"owner={owner}",
                f"action={_dsl_quote(next_step)}",
            ]
        ),
        f"#902 act=replay shell={_dsl_quote(replay_command, max_len=1000)}",
        f"#903 act=validate shell={_dsl_quote(validate_command, max_len=1000)}",
    ]


def action_snapshot(
    args: argparse.Namespace,
    *,
    client_fn: Any | None = None,
) -> int:
    """Print a unified shell OQL/DSL snapshot with replay/validate commands."""
    project = Path(args.project).resolve()
    ide = canonical_autopilot_ide_id(normalize_ide_id(str(args.ide)))
    if client_fn is None:
        from koru.autopilot.client import AutopilotClient

        client = AutopilotClient(
            socket_path=getattr(args, "socket", None),
            project=project,
            ide=ide,
        )
    else:
        client = client_fn(args)
    limit = max(0, int(args.limit or 12))
    ticket = str(args.ticket).strip() if getattr(args, "ticket", None) else None

    lines: list[str] = []
    skip_code = "unknown"
    info: dict[str, Any] = {}

    if not client.is_running():
        lines.extend(
            [
                f"#001 act=runtime intent=\"daemon health\" route=socket:{client.socket_path} ok=false "
                f'reason="daemon is not running"',
            ]
        )
    else:
        try:
            info = client.status()
        except (OSError, RuntimeError) as exc:
            lines.append(
                f"#001 act=runtime intent=\"daemon health\" route=socket:{client.socket_path} "
                f"ok=false reason={_dsl_quote(exc)}"
            )
        else:
            lines.extend(
                _runtime_lines(
                    project=project,
                    ide=ide,
                    socket_path=str(client.socket_path),
                    info=info,
                )
            )

    decision_lines = _decision_lines(project, limit=1)
    lines.extend(decision_lines)
    if decision_lines:
        for token in decision_lines[0].split():
            if token.startswith("code="):
                skip_code = token.split("=", 1)[1]

    lines.extend(_observe_path_line(project, ticket=ticket, limit=limit))
    lines.extend(_drive_dsl_lines(project, limit=limit))
    if args.include_env2llm:
        lines.extend(_env2llm_lines(project))

    lane_env = _lane_shell_env(
        project=project,
        ide=ide,
        socket_path=str(client.socket_path),
    )
    replay_shells = [
        f"{lane_env} koru autopilot status --ide {ide} --explain --project {shlex.quote(str(project))}",
        f"koru observe trace --project {shlex.quote(str(project))} --format path --limit {limit}",
        f"koru autopilot trace --project {shlex.quote(str(project))} --format drive-dsl --limit {limit}",
        f"{lane_env} koru replay 'ide connect-plugin {ide}' --explain",
    ]
    if args.include_env2llm:
        replay_shells.append(
            f"ENV2LLM_DESKTOP_PROBE=1 env2llm {shlex.quote(str(project))} --probe-desktop"
        )
    lines.extend(
        _operator_lines(
            project=project,
            ide=ide,
            socket_path=str(client.socket_path),
            info=info,
            skip_code=skip_code,
        )
    )
    for idx, shell in enumerate(replay_shells, start=904):
        lines.append(f"#{idx:03d} act=replay shell={_dsl_quote(shell, max_len=1000)}")

    print("\n".join(lines))
    return 0 if client.is_running() else 1


__all__ = ["action_snapshot"]
