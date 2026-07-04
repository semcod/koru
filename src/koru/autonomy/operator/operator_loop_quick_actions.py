"""Quick-action lines and replayable control commands for ``koru autonomous``."""

from __future__ import annotations

import shlex
from typing import Any
from urllib.parse import parse_qs, urlparse

from koru.autonomy.operator.operator_loop_interfaces import (
    _blocked_by_from_autopilot_status,
    _is_plugin_blocker,
    _safe_dashboard_action_urls,
)
from koru.autonomy.operator.operator_loop_reporting import _slug
from koru.autonomy.replay_actions import quick_action_to_replay


def _base_quick_action_lines() -> list[str]:
    return [
        "[show decision trace] `curl -s http://127.0.0.1:8765/api/autonomy/trace | jq .decisions`",
        (
            "[show interfaces] "
            "`curl -s http://127.0.0.1:8765/api/interfaces | jq '.families, .blockers'`"
        ),
    ]


def _autopilot_quick_action_lines(
    *,
    status: str,
    blocked_by: str,
    autopilot_ide: str,
) -> list[str]:
    # Late-bind through the runner facade so tests patching
    # ``autonomous_loop_runner._blocked_interface_action_lines`` still take effect.
    from koru.autonomy.operator import operator_loop_runner as _runner_mod

    autopilot_actions = _runner_mod._blocked_interface_action_lines(
        blocked_by, autopilot_ide=autopilot_ide
    )
    if _is_plugin_blocker(blocked_by):
        autopilot_actions.append(
            "[reconnect plugin] in IDE: Command Palette → `Developer: Reload Window`, "
            "then `koru: Connect autopilot daemon`"
        )
    if "ide_mismatch" in status:
        autopilot_actions.append(
            "[switch lane] export KORU_AUTOPILOT_INSTANCE=<ide> "
            "(or rerun `koru auto --autopilot-ide <ide>`)"
        )
    if "chat_activity" in status:
        autopilot_actions.append(
            "[pause autopilot 10m] "
            "`touch .planfile/.koru/autopilot-pause-until-$(date +%s -d '+10 minutes')`"
        )
    return autopilot_actions


def _queue_quick_action_lines(
    *,
    status: str,
    queue_status: str,
    waiting_ticket: str,
    autopilot_ide: str,
    urls: dict[str, str],
) -> list[str]:
    queue_actions: list[str] = []
    if "idle_no_ticket" in status or queue_status == "idle":
        queue_actions.append(f"[create ticket] {urls['create_project_ticket_action']}")
        queue_actions.append(f"[reopen done ticket] {urls['tickets']}")
        queue_actions.append(
            "[force fresh scan] `rm -rf project/ && KORU_SCAN_FORCE_RESCAN=1 koru auto`"
        )
    if queue_status == "waiting_input" and waiting_ticket and waiting_ticket != "-":
        if "stuck_waiting_input" in status:
            queue_actions.append(
                "[auto llm-ready] enabled by default; set "
                "`KORU_AUTOPILOT_AUTO_LLM_READY=0` to require manual approval"
            )
        queue_actions.append(
            f"[mark ticket input] `planfile ticket input {waiting_ticket} "
            "--prompt '<input needed>' --note '<what was verified>'`"
        )
        queue_actions.append(f"[open ticket] {urls['tickets']}#{waiting_ticket}")
    if "submit_unverified" in status:
        queue_actions.append(
            "[validate submit trace] "
            "`koru autopilot trace --project . --format drive-dsl --limit 30`"
        )
        queue_actions.append(
            f"[manual send required] `planfile ticket input {waiting_ticket} "
            "--prompt 'Manual IDE action required: submit was not verified' "
            "--note 'Koru pasted the prompt but refused unsafe host fallback; "
            "send manually or fix plugin submit strategy'`"
        )
    elif status.startswith("failed"):
        queue_actions.append(
            "[validate drive trace] "
            "`koru autopilot trace --project . --format drive-dsl --limit 30`"
        )
        queue_actions.append(
            f"[mark ticket input] `planfile ticket input {waiting_ticket} "
            "--prompt 'Manual IDE action required: autopilot drive failed' "
            "--note 'Koru did not verify a safe submitted message; inspect drive trace before retrying'`"
        )
    return queue_actions


def _diagnostics_quick_action_lines(status: str) -> list[str]:
    if "diagnostics_fail" not in status:
        return []
    return [
        "[show wup track] `ls -t .wup/tracks/*_quick.json | head -1 | xargs cat`",
        (
            "[show wup failures] "
            "`curl -s http://127.0.0.1:8765/api/dashboard 2>/dev/null | "
            "jq '.wup.health' || cat .wup/service-health.json`"
        ),
        (
            "[disable diagnostics gate] "
            "`koru auto --no-autopilot-skip-on-diagnostics-fail` "
            "(or env: KORU_AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL=0)"
        ),
    ]


def _quick_action_lines(
    *,
    project: Any | None,
    queue_status: str,
    waiting_ticket: str,
    autopilot_status: str,
    autopilot_ide: str = "",
) -> list[str]:
    """Concrete one-liners the operator can copy/paste right now.

    Returns ``[label] cmd-or-link`` items tailored to the current state.
    Each item is a separate line so the operator log stays grep-friendly.

    The set is intentionally small (≤ 6 actions) so the output does NOT
    drown out the next-step narrative. Items only appear when they are
    actually relevant to the current cycle.
    """
    urls = _safe_dashboard_action_urls(project)
    status = (autopilot_status or "").lower()
    queue_status = (queue_status or "").lower()
    blocked_by = _blocked_by_from_autopilot_status(autopilot_status)

    quick_actions = _base_quick_action_lines()
    quick_actions.extend(
        _autopilot_quick_action_lines(
            status=status,
            blocked_by=blocked_by,
            autopilot_ide=autopilot_ide,
        )
    )
    quick_actions.extend(
        _queue_quick_action_lines(
            status=status,
            queue_status=queue_status,
            waiting_ticket=waiting_ticket,
            autopilot_ide=autopilot_ide,
            urls=urls,
        )
    )
    quick_actions.extend(_diagnostics_quick_action_lines(status))
    return _replay_quick_action_lines(
        quick_actions,
        autopilot_ide=autopilot_ide,
        waiting_ticket=waiting_ticket,
        base_url=_url_origin(urls.get("dashboard", "http://127.0.0.1:8765/")),
    )


def _replay_quick_action_lines(
    quick_actions: list[str],
    *,
    autopilot_ide: str,
    waiting_ticket: str,
    base_url: str,
) -> list[str]:
    replay_lines: list[str] = []
    for action in quick_actions:
        label, body = _split_quick_action(action)
        # Keep ticket links as plain URLs so operators can reuse the active dashboard tab
        # instead of triggering a separate replay shell path.
        if label == "open ticket" and body.startswith(("http://", "https://")):
            replay_lines.append(action)
            continue
        replay = quick_action_to_replay(
            action,
            autopilot_ide=autopilot_ide,
            waiting_ticket=waiting_ticket,
            base_url=base_url,
        )
        if replay is None:
            replay_lines.append(action)
            continue
        shell = replay.to_shell()
        if not replay.replayable:
            shell = f"{shell} --explain"
        replay_lines.append(f"[{label}] `{shell}`")
    return replay_lines


def _record_quick_action_control_commands(
    *,
    project: Any | None,
    waiting_ticket: str,
    autopilot_status: str,
    autopilot_ide: str,
    quick_actions: list[str],
) -> None:
    if project is None:
        return
    try:
        from pathlib import Path

        project_path = Path(project)
    except TypeError:
        return
    if not project_path.exists():
        return
    corr_ticket = waiting_ticket if waiting_ticket and waiting_ticket != "-" else "none"
    blocker = _blocked_by_from_autopilot_status(autopilot_status) or "none"
    corr = f"operator-action-{corr_ticket}-{blocker}"
    for action in quick_actions:
        _record_quick_action_control_command(
            project_path,
            corr=corr,
            action=action,
            autopilot_ide=autopilot_ide,
        )


def _record_quick_action_control_command(
    project: Any,
    *,
    corr: str,
    action: str,
    autopilot_ide: str,
) -> None:
    label, body = _split_quick_action(action)
    if label == "reconnect plugin":
        _record_reconnect_plugin_command(project, corr=corr, autopilot_ide=autopilot_ide)
        return
    command = _backtick_command(body)
    if command:
        _record_backtick_command(project, corr=corr, label=label, command=command)
        return
    if body.startswith("http://") or body.startswith("https://"):
        _record_url_command(project, corr=corr, label=label, url=body)
        return


def _split_quick_action(action: str) -> tuple[str, str]:
    text = str(action).strip()
    if text.startswith("[") and "]" in text:
        label, body = text[1:].split("]", 1)
        return label.strip(), body.strip()
    return "", text


def _backtick_command(text: str) -> str:
    if "`" not in text:
        return ""
    try:
        return text.split("`", 2)[1].strip()
    except IndexError:
        return ""


def _record_backtick_command(project: Any, *, corr: str, label: str, command: str) -> None:
    from koru.control_commands import shell_command

    _record_replay_sidecar_command(project, corr=corr, command=command)
    url = _curl_url(command)
    if url:
        _record_url_command(project, corr=corr, label=label, url=url)
    shell_command(
        project,
        corr=f"{corr}:{_slug(label or 'shell')}:shell",
        argv=["bash", "-lc", command],
        actor="autonomy-next",
    )


def _record_replay_sidecar_command(project: Any, *, corr: str, command: str) -> None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return
    if len(parts) < 3 or parts[:2] != ["koru", "replay"]:
        return
    try:
        from koru.autonomy.replay_actions import parse_replay_dsl

        action = parse_replay_dsl(parts[2])
    except Exception:
        return
    if action.domain == "trace" and action.verb == "show-decisions":
        _record_url_command(
            project,
            corr=corr,
            label="show decision trace",
            url=f"{action.args.get('url', 'http://127.0.0.1:8765').rstrip('/')}/api/autonomy/trace",
        )
    elif action.domain == "trace" and action.verb == "show-interfaces":
        _record_url_command(
            project,
            corr=corr,
            label="show interfaces",
            url=f"{action.args.get('url', 'http://127.0.0.1:8765').rstrip('/')}/api/interfaces",
        )
    elif action.domain == "ticket" and action.verb == "open":
        _record_url_command(
            project,
            corr=corr,
            label="open ticket",
            url=f"{action.args.get('url', 'http://127.0.0.1:8765')}#{action.positional[0] if action.positional else ''}",
        )


def _curl_url(command: str) -> str:
    parts = shlex.split(command)
    for part in parts:
        if part.startswith(("http://", "https://")):
            return part
    return ""


def _url_origin(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return "http://127.0.0.1:8765"


def _record_url_command(project: Any, *, corr: str, label: str, url: str) -> None:
    from koru.control_commands import api_command

    parsed = urlparse(url)
    path = parsed.path or "/"
    query = {
        key: values[-1] if len(values) == 1 else values
        for key, values in parse_qs(parsed.query).items()
    }
    if parsed.fragment:
        query["_fragment"] = parsed.fragment
    api_command(
        project,
        corr=f"{corr}:{_slug(label or path)}:api",
        method="GET",
        path=path,
        query=query,
        actor="autonomy-next",
    )


def _record_reconnect_plugin_command(project: Any, *, corr: str, autopilot_ide: str) -> None:
    from koru.control_commands import desktop_gui_command

    desktop_gui_command(
        project,
        corr=f"{corr}:reconnect-plugin:desktop",
        operation="command_palette_sequence",
        backend="command_palette",
        target=autopilot_ide or "ide",
        payload={
            "commands": [
                "Developer: Reload Window",
                "koru: Connect autopilot daemon",
            ],
        },
        actor="operator",
        replayable=False,
    )


def _emit_quick_action_line(*, args: Any, action: str, stdio_info: Any) -> None:
    line = f"koru autonomous: action {action}"
    if _is_create_ticket_action(action):
        from koru.activity_log import activity_warn

        activity_warn(
            line,
            hint=(
                "ważne: queue jest idle i planfile zgłasza brak otwartych ticketów; "
                "utwórz ticket, żeby autonomia miała zadanie do wykonania"
            ),
            fmt=args.emit_events,
            data={"action": "create_ticket", "blocked_by": "idle_no_ticket"},
        )
        return
    stdio_info(line, fmt=args.emit_events)


def _is_create_ticket_action(action: str) -> bool:
    label, _body = _split_quick_action(action)
    return label == "create ticket"
