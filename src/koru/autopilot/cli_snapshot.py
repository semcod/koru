"""``koru autopilot snapshot`` — copy-pasteable shell OQL/DSL runtime view."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from typing import Any

from koru.autopilot.cli_snapshot_lines import _bridge_line as _bridge_line
from koru.autopilot.cli_snapshot_lines import _calibration_line as _calibration_line
from koru.autopilot.cli_snapshot_lines import _daemon_detail as _daemon_detail
from koru.autopilot.cli_snapshot_lines import _decision_lines as _decision_lines
from koru.autopilot.cli_snapshot_lines import _drive_dsl_lines as _drive_dsl_lines
from koru.autopilot.cli_snapshot_lines import _dsl_quote as _dsl_quote
from koru.autopilot.cli_snapshot_lines import _env2llm_desktop_lines as _env2llm_desktop_lines
from koru.autopilot.cli_snapshot_lines import _env2llm_error_line as _env2llm_error_line
from koru.autopilot.cli_snapshot_lines import _env2llm_lines as _env2llm_lines
from koru.autopilot.cli_snapshot_lines import _env2llm_unavailable_error as _env2llm_unavailable_error
from koru.autopilot.cli_snapshot_lines import _filter_drive_lines as _filter_drive_lines
from koru.autopilot.cli_snapshot_lines import _live_desktop_probe as _live_desktop_probe
from koru.autopilot.cli_snapshot_lines import _observe_path_line as _observe_path_line
from koru.autopilot.cli_snapshot_lines import _plugin_labels as _plugin_labels
from koru.autopilot.cli_snapshot_lines import _runtime_lines as _runtime_lines
from koru.autopilot.cli_snapshot_lines import (
    _skip_code_from_decision_lines as _skip_code_from_decision_lines,
)
from koru.autopilot.lane_context import instance_from_socket_path, resolve_lane_context
from koru.ide_adapters.bridge import evaluate_bridge, format_bridge_text
from koruide.ide import canonical_autopilot_ide_id, normalize_ide_id


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


def _snapshot_runtime_block(
    client: Any,
    *,
    project: Path,
    ide: str,
) -> tuple[list[str], dict[str, Any]]:
    """Daemon health/plugin/bridge lines plus the fetched status payload."""
    lines: list[str] = []
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
    return lines, info


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

    lines, info = _snapshot_runtime_block(client, project=project, ide=ide)

    decision_lines = _decision_lines(project, limit=1)
    lines.extend(decision_lines)
    skip_code = _skip_code_from_decision_lines(decision_lines)

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
