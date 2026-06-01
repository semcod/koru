"""Outer-loop runner for ``koru autonomous`` cycles."""

from __future__ import annotations

import os
import shlex
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse

_AUTOPILOT_BLOCKED_QUEUE_STATUSES = frozenset({"waiting_input"})

from koru.autonomy.structured_report import emit_structured_cycle_report
from koru.autonomy.replay_actions import quick_action_to_replay



def _blocked_by_from_autopilot_status(autopilot_status: str) -> str:
    status = (autopilot_status or "").strip().lower()
    if "submit_unverified" in status or "submit_failed" in status:
        return "manual_send_required"
    if status.startswith("skipped("):
        return status[len("skipped("):].rstrip(")").strip()
    if status.startswith("failed"):
        return "drive_failed"
    return ""


def _is_plugin_blocker(blocked_by: str) -> bool:
    key = (blocked_by or "").strip().lower()
    return key.startswith("plugin_")


def _interface_matches_ide(interface_id: str, target_ide: str) -> bool:
    ide = (target_ide or "").strip().lower()
    if not ide or ide == "auto":
        return True
    if ide == "jetbrains":
        return "jetbrains" in interface_id
    if ide == "antigravity":
        return interface_id in {"plugin_socket_vscode_family", "antigravity_native_send"}
    if ide in {"cursor", "vscode", "vscodium", "windsurf"}:
        return interface_id == "plugin_socket_vscode_family"
    return True


def _blocked_interface_action_lines(
    blocked_by: str,
    *,
    autopilot_ide: str = "",
) -> list[str]:
    key = (blocked_by or "").strip()
    if not key:
        return []
    try:
        from koru.interface_registry import blocker_interface_payload

        payload = blocker_interface_payload(key)
    except Exception:
        return []
    items = _blocked_interface_items(payload)
    if not items:
        return []
    selected = _select_blocked_interface_items(items, autopilot_ide)
    return [_format_blocked_interface_line(item) for item in selected if item.get("id")]


def _blocked_interface_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("interfaces")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _select_blocked_interface_items(
    items: list[dict[str, Any]],
    autopilot_ide: str,
) -> list[dict[str, Any]]:
    matching_items = [
        item
        for item in items
        if _interface_matches_ide(str(item.get("id") or "").strip(), autopilot_ide)
    ]
    return (matching_items or items)[:2]


def _format_blocked_interface_line(item: dict[str, Any]) -> str:
    interface_id = str(item.get("id") or "").strip()
    return (
        f"[blocked interface] {interface_id}"
        f"{_blocked_interface_detail_suffix(item)}"
        f"{_blocked_interface_recovery_suffix(item)}"
    )


def _blocked_interface_detail_suffix(item: dict[str, Any]) -> str:
    details = [
        f"{key}={value}"
        for key in ("family", "transport")
        if (value := str(item.get(key) or "").strip())
    ]
    return f" ({', '.join(details)})" if details else ""


def _blocked_interface_recovery_suffix(item: dict[str, Any]) -> str:
    recovery = item.get("operator_recovery")
    if not isinstance(recovery, list):
        return ""
    steps = [str(step).strip() for step in recovery if str(step).strip()]
    return " ; recovery: " + " | ".join(steps[:2]) if steps else ""


def _dashboard_action_urls(project: Any) -> dict[str, str]:
    base = "http://127.0.0.1:8765"
    try:
        from pathlib import Path
        from urllib.parse import urlencode

        from koruapi.dashboard_serve import read_serve_endpoint

        endpoint = read_serve_endpoint(Path(project))
        if isinstance(endpoint, dict):
            raw_base = str(endpoint.get("http_base") or "").strip()
            if raw_base:
                base = raw_base.rstrip("/")
        query = urlencode({"project": str(Path(project).resolve())})
    except Exception:
        query = ""
    suffix = f"?{query}" if query else ""
    return {
        "dashboard": f"{base}/{suffix}",
        "create_project_ticket": f"{base}/llm/prompt/create-ticket-for-project{suffix}",
        "create_project_ticket_action": f"{base}/llm/action/create-ticket-for-project{suffix}",
        "tickets": f"{base}/?tab=tickets{('&' + query) if query else ''}",
    }


def _default_dashboard_action_urls() -> dict[str, str]:
    return {
        "dashboard": "http://127.0.0.1:8765/",
        "create_project_ticket": "http://127.0.0.1:8765/llm/prompt/create-ticket-for-project",
        "create_project_ticket_action": "http://127.0.0.1:8765/llm/action/create-ticket-for-project",
        "tickets": "http://127.0.0.1:8765/?tab=tickets",
    }


def _safe_dashboard_action_urls(project: Any | None) -> dict[str, str]:
    if project is None:
        return _default_dashboard_action_urls()
    try:
        return _dashboard_action_urls(project)
    except Exception:
        return _default_dashboard_action_urls()


def _handle_stop_reason_waiting_input(ticket: str, **kwargs: Any) -> list[str]:
    return [
        f"1/3 stop now; queue is waiting for operator input on {ticket}",
        f"2/3 operator should mark {ticket} done/input/fail through planfile",
        "3/3 next koru auto run will resume from the updated queue state",
    ]


def _handle_stop_reason_max_cycles(args: Any, status: str, ticket: str, **kwargs: Any) -> list[str]:
    return [
        f"1/3 stop now; reached max-cycles={getattr(args, 'max_cycles', '?')}",
        f"2/3 preserve checkpoint with queue={status or 'unknown'} waiting={ticket}",
        "3/3 next koru auto run will continue from the saved checkpoint",
    ]


def _handle_status_waiting_input(
    sleep_text: str,
    ticket: str,
    autopilot_status: str,
    max_iterations: int,
    **kwargs: Any,
) -> list[str]:
    if "chat_activity" in autopilot_status:
        first = (
            f"1/3 wait {sleep_text}; chat cooldown is active for {ticket}, "
            "so Koru will not paste over the IDE chat; this is not a daemon failure"
        )
    elif _is_plugin_blocker(_blocked_by_from_autopilot_status(autopilot_status)):
        first = (
            f"1/3 wait {sleep_text}; keep queue on {ticket} while the IDE "
            "plugin reconnects"
        )
    else:
        first = f"1/3 wait {sleep_text}; keep current waiting ticket {ticket} scoped"
    return [
        first,
        f"2/3 rerun planfile queue (max {max_iterations}) and check whether {ticket} moved",
        (
            "3/3 if queue becomes idle, run scan/discovery; if still waiting, "
            "use chat events/reflection before any redrive"
        ),
    ]


def _handle_status_idle(args: Any, project: Any, sleep_text: str, **kwargs: Any) -> list[str]:
    urls = _dashboard_action_urls(project) if project is not None else {
        "dashboard": "http://127.0.0.1:8765/",
        "create_project_ticket": "http://127.0.0.1:8765/llm/prompt/create-ticket-for-project",
        "create_project_ticket_action": "http://127.0.0.1:8765/llm/action/create-ticket-for-project",
        "tickets": "http://127.0.0.1:8765/?tab=tickets",
    }
    discovery = (
        "scan/code2llm discovery if freshness and rate limits allow"
        if getattr(args, "scan_after_idle_queue", False)
        else "idle scan is disabled unless explicitly requested"
    )
    return [
        (
            f"1/3 wait {sleep_text}; queue is idle — all planfile tickets "
            "are 'done' or canceled. autopilot drive is suppressed so the "
            "user's chat input isn't clobbered with stale prompts"
        ),
        (
            "2/3 strategy detail→general: planfile ticket queue first; "
            f"when empty, {discovery}; then code2llm whole-project discovery "
            "can create new focused tickets"
        ),
        (
            "3/3 quick links: create discovery ticket "
            f"{urls['create_project_ticket_action']} ; tickets {urls['tickets']} ; "
            "force fresh scan command remains: "
            "`rm -rf project/ && KORU_SCAN_FORCE_RESCAN=1 koru auto`"
        ),
    ]


def _handle_status_completed_or_failed(
    status: str,
    sleep_text: str,
    max_iterations: int,
    **kwargs: Any,
) -> list[str]:
    return [
        f"1/3 wait {sleep_text}; queue just reported {status}",
        f"2/3 rerun planfile queue (max {max_iterations}) to pick the next ticket",
        "3/3 if no ticket remains, switch to idle scan/discovery strategy",
    ]


def _handle_default_steps(
    sleep_text: str,
    stagnation_streak: int,
    status: str,
    **kwargs: Any,
) -> list[str]:
    return [
        f"1/3 wait {sleep_text}; preserve current loop state (streak={stagnation_streak})",
        f"2/3 rerun queue/status checks for status={status or 'unknown'}",
        "3/3 choose scan, ticket drive, or operator input based on the next queue result",
    ]


class AutonomyNextStepNarrator:
    """Build exactly three operator-facing next-step lines per cycle."""

    def __init__(
        self,
        *,
        args: Any,
        project: Any | None,
        waiting_ticket: str,
    ) -> None:
        self.args = args
        self.project = project
        self.waiting_ticket = waiting_ticket if waiting_ticket and waiting_ticket != "-" else "none"

    def narrate(
        self,
        *,
        queue_status: str,
        autopilot_status: str,
        sleep_seconds: float,
        stagnation_streak: int,
        stop_reason: str | None,
    ) -> list[str]:
        sleep_text = f"{sleep_seconds:g}s"
        max_iterations = int(getattr(self.args, "max_iterations", 50) or 50)

        kwargs = {
            "args": self.args,
            "project": self.project,
            "waiting_ticket": self.waiting_ticket,
            "autopilot_status": autopilot_status,
            "effective_sleep": sleep_seconds,
            "stagnation_streak": stagnation_streak,
            "stop_reason": stop_reason,
            "status": queue_status,
            "max_iterations": max_iterations,
            "ticket": self.waiting_ticket,
            "sleep_text": sleep_text,
        }

        if stop_reason == "waiting_input":
            return _handle_stop_reason_waiting_input(**kwargs)
        if stop_reason == "max_cycles":
            return _handle_stop_reason_max_cycles(**kwargs)
        if queue_status == "waiting_input":
            return _handle_status_waiting_input(**kwargs)
        if queue_status == "idle":
            return _handle_status_idle(**kwargs)
        if queue_status in {"completed", "failed"}:
            return _handle_status_completed_or_failed(**kwargs)

        return _handle_default_steps(**kwargs)


def _operator_next_steps(
    *,
    args: Any,
    project: Any | None = None,
    queue_result: Any,
    waiting_ticket: str,
    autopilot_status: str,
    effective_sleep: float,
    stagnation_streak: int,
    stop_reason: str | None = None,
) -> list[str]:
    """Human-readable plan for the next outer-loop moves."""
    narrator = AutonomyNextStepNarrator(
        args=args,
        project=project,
        waiting_ticket=waiting_ticket,
    )
    return narrator.narrate(
        queue_status=str(getattr(queue_result, "last_status", "") or ""),
        autopilot_status=autopilot_status,
        sleep_seconds=effective_sleep,
        stagnation_streak=stagnation_streak,
        stop_reason=stop_reason,
    )


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
    autopilot_actions = _blocked_interface_action_lines(blocked_by, autopilot_ide=autopilot_ide)
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


def _should_warn_idle_no_ticket(
    *,
    queue_status: str,
    waiting_ticket: str,
    autopilot_status: str,
) -> bool:
    if waiting_ticket and waiting_ticket != "-":
        return False
    status = (autopilot_status or "").strip().lower()
    queue = (queue_status or "").strip().lower()
    return queue == "idle" or "idle_no_ticket" in status


def _idle_no_ticket_warning(project: Any | None) -> tuple[str, str, dict[str, Any]]:
    urls = _safe_dashboard_action_urls(project)
    message = "autonomia nie wykonuje zadania: brak otwartych ticketów w planfile"
    hint = (
        "plan: szczegół→ogół — najpierw planfile queue, potem idle scan/code2llm; "
        "workflow standaryzowany: gdy po scan/code2llm brak pracy, system "
        "auto-tworzy/reuzywa ticket discovery dla IDE LLM; "
        "jezeli nadal brak ruchu, zlec IDE LLM pytanie: "
        "'Co jeszcze zostalo do wykonania? zrob z tego nastepne tickety do planfile.' "
        "i zamien odpowiedz na tickety; "
        "prefact/metrun są narzędziami advisory bez automatycznych adapterów ticketów. "
        f"Napisz ticket w Web GUI: {urls['create_project_ticket']} ; "
        f"lista ticketów: {urls['tickets']}"
    )
    data = {
        "blocked_by": "idle_no_ticket",
        "create_ticket_url": urls["create_project_ticket"],
        "tickets_url": urls["tickets"],
    }
    return message, hint, data


def _emit_idle_no_ticket_warning(
    *,
    args: Any,
    project: Any | None,
    queue_status: str,
    waiting_ticket: str,
    autopilot_status: str,
) -> None:
    if not _should_warn_idle_no_ticket(
        queue_status=queue_status,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
    ):
        return
    from koru.activity_log import activity_warn

    message, hint, data = _idle_no_ticket_warning(project)
    activity_warn(message, hint=hint, fmt=args.emit_events, data=data)


def _slug(value: str) -> str:
    return "-".join(
        part
        for part in "".join(ch.lower() if ch.isalnum() else "-" for ch in value).split("-")
        if part
    )[:48]


def _current_mission_lines(
    *,
    queue_result: Any,
    waiting_ticket: str,
    autopilot_status: str,
    effective_sleep: float,
) -> list[str]:
    """Compact mission snapshot for the operator shell.

    Gives one stable place to see the current ticket, blocker, and next
    expected movement without reading the whole cycle transcript.
    """
    queue_status = str(getattr(queue_result, "last_status", "") or "unknown")
    if not waiting_ticket or waiting_ticket == "-":
        return []
    blocker = _blocked_by_from_autopilot_status(autopilot_status) or "none"
    line_1 = (
        "koru autonomous: current mission "
        f"ticket={waiting_ticket} queue={queue_status} blocker={blocker}"
    )
    if _is_plugin_blocker(blocker):
        line_2 = (
            "koru autonomous: current mission next="
            "reload/reconnect plugin, then rerun queue for the same ticket"
        )
    elif blocker == "chat_activity":
        line_2 = (
            "koru autonomous: current mission next="
            f"wait {effective_sleep:g}s for chat cooldown, then reconsider redrive "
            "(tune: KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS)"
        )
    elif queue_status == "waiting_input":
        line_2 = (
            "koru autonomous: current mission next="
            "operator or IDE work must move the ticket out of waiting_input"
        )
    else:
        line_2 = (
            "koru autonomous: current mission next="
            "recheck queue state and continue the same ticket"
        )
    return [line_1, line_2]


def _log_operator_next_steps(
    *,
    args: Any,
    project: Any | None,
    queue_result: Any,
    waiting_ticket: str,
    autopilot_status: str,
    effective_sleep: float,
    loop_state: Any,
    stop_reason: str | None,
    stdio_info: Any,
    autopilot_ide: str = "",
) -> None:
    for line in _current_mission_lines(
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        effective_sleep=effective_sleep,
    ):
        stdio_info(line, fmt=args.emit_events)
    for line in _operator_next_steps(
        args=args,
        project=project,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        effective_sleep=effective_sleep,
        stagnation_streak=int(getattr(loop_state, "stagnation_streak", 0) or 0),
        stop_reason=stop_reason,
    ):
        stdio_info(f"koru autonomous: next {line}", fmt=args.emit_events)
    quick_action_lines = _quick_action_lines(
        project=project,
        queue_status=str(getattr(queue_result, "last_status", "") or ""),
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
    )
    _record_quick_action_control_commands(
        project=project,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        quick_actions=quick_action_lines,
    )
    for action in quick_action_lines:
        _emit_quick_action_line(args=args, action=action, stdio_info=stdio_info)


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


def _cycle_stop_reason(args: Any, queue_result: Any, cycle: int) -> str | None:
    if (
        getattr(args, "stop_on_waiting_input", False)
        and queue_result.last_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES
    ):
        return "waiting_input"
    max_cycles = int(getattr(args, "max_cycles", 0) or 0)
    if max_cycles > 0 and cycle >= max_cycles:
        return "max_cycles"
    return None


def handle_cycle_exit_conditions(
    args: Any,
    queue_result: Any,
    cycle: int,
    correlation_id: str,
    *,
    write_event: Any,
    stdio_info: Any,
    output_stream: Any = sys.stdout,
) -> bool:
    """Return True when the autonomous loop should stop after a cycle."""
    stop_reason = _cycle_stop_reason(args, queue_result, cycle)
    if stop_reason == "waiting_input":
        if args.emit_events == "jsonl":
            write_event(
                output_stream,
                event_type="AutonomousStopped",
                correlation_id=correlation_id,
                payload={"reason": "waiting_input", "cycle": cycle},
            )
        stdio_info(
            "koru autonomous: queue is waiting_input; stopping until "
            "human/manual ticket recovery marks it ready or done",
            fmt=args.emit_events,
        )
        return True

    if stop_reason == "max_cycles":
        if args.emit_events == "jsonl":
            write_event(
                output_stream,
                event_type="AutonomousStopped",
                correlation_id=correlation_id,
                payload={
                    "reason": "max_cycles",
                    "cycle": cycle,
                    "max_cycles": args.max_cycles,
                },
            )
        stdio_info(
            f"koru autonomous: reached max-cycles={args.max_cycles}; stopping",
            fmt=args.emit_events,
        )
        return True
    return False


def _save_cycle_checkpoint(
    *,
    checkpoint_path: Any,
    cycle: int,
    loop_state: Any,
    queue_result: Any,
    queue_loop_waiting_ticket_label: Any,
    save_loop_checkpoint: Any,
) -> str:
    waiting_ticket = queue_loop_waiting_ticket_label(queue_result)
    save_loop_checkpoint(
        checkpoint_path,
        cycle=cycle,
        state=loop_state,
        queue_status=queue_result.last_status,
        waiting_ticket=waiting_ticket,
    )
    return waiting_ticket


def _cycle_idle_context(project: Any, queue_result: Any) -> str:
    if queue_result.last_status != "idle":
        return ""
    from koru.autonomy.ide_work import sprint_ticket_status_summary

    return f" {sprint_ticket_status_summary(project)}"


def _emit_cycle_summary(
    *,
    args: Any,
    project: Any,
    cycle: int,
    queue_result: Any,
    waiting_ticket: str,
    loop_state: Any,
    diag_result: Any,
    autopilot_status: str,
    effective_sleep: float,
    stdio_info: Any,
) -> None:
    idle_context = _cycle_idle_context(project, queue_result)
    stdio_info(
        f"koru autonomous: summary cycle={cycle} queue={queue_result.last_status} "
        f"waiting={waiting_ticket} "
        f"streak={loop_state.stagnation_streak} diagnostics={diag_result.status} "
        f"autopilot={autopilot_status} sleep={effective_sleep}s{idle_context}",
        fmt=args.emit_events,
    )


def _emit_structured_report(
    *,
    args: Any,
    cycle: int,
    queue_result: Any,
    waiting_ticket: str,
    loop_state: Any,
    diag_result: Any,
    autopilot_status: str,
    autopilot_ide: str,
    effective_sleep: float,
) -> None:
    if args.emit_events != "human":
        return
    if os.environ.get("KORU_STRUCTURED_CYCLE_REPORT", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return

    from koru.activity_log import activity

    def activity_fn(category: str, message: str) -> None:
        activity(category, message, fmt="human")

    emit_structured_cycle_report(
        cycle=cycle,
        queue_status=str(getattr(queue_result, "last_status", "") or ""),
        waiting_ticket=waiting_ticket,
        wup_status=str(getattr(loop_state, "wup_status", "ok")),
        diag_status=str(getattr(diag_result, "status", "") or ""),
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        stagnation_streak=int(getattr(loop_state, "stagnation_streak", 0) or 0),
        sleep_seconds=effective_sleep,
        activity_fn=activity_fn,
    )


def _print_cycle_header(args: Any, cycle: int) -> None:
    if args.emit_events == "human":
        print(f"\n=== koru autonomous cycle #{cycle} ===")


def _prepare_cycle_run(
    *,
    args: Any,
    project: Any,
    client: Any,
    daemon: Any,
    thread: Any,
    socket_path: Any,
    autopilot_socket_observed_at_boot: bool,
    queue_name: str | None,
    enable_scan: bool,
    autopilot_ide: str,
    loop_state: Any,
    diagnostic_state_dir: Any,
    wup_process: Any | None,
    correlation_id: str,
    auto_pipeline_state: Any | None,
    cycle: int,
    restart_daemon_if_needed: Any,
    select_and_log_cycle_profile: Any,
    resolve_effective_cycle_flags: Any,
    build_cycle_run_kwargs: Any,
) -> dict[str, Any]:
    client, daemon, thread = restart_daemon_if_needed(
        args,
        client,
        socket_path,
        daemon,
        thread,
        autopilot_socket_observed_at_boot,
        project,
    )
    profile = select_and_log_cycle_profile(
        args,
        auto_pipeline_state,
        enable_scan=enable_scan,
    )
    effective_enable_scan, _effective_enable_autopilot = resolve_effective_cycle_flags(
        args,
        profile,
        enable_scan=enable_scan,
        loop_state=loop_state,
        client=client,
        autopilot_ide=autopilot_ide,
    )
    return build_cycle_run_kwargs(
        args,
        profile,
        cycle=cycle,
        project=project,
        queue_name=queue_name,
        enable_scan=effective_enable_scan,
        autopilot_ide=autopilot_ide,
        client=client,
        loop_state=loop_state,
        diagnostic_state_dir=diagnostic_state_dir,
        wup_process=wup_process,
        correlation_id=correlation_id,
    )


def _run_cycle_and_checkpoint(
    *,
    cycle_kwargs: dict[str, Any],
    cycle: int,
    loop_state: Any,
    checkpoint_path: Any,
    auto_pipeline_state: Any | None,
    run_cycle: Any,
    update_auto_pipeline_state: Any,
    save_loop_checkpoint: Any,
    queue_loop_waiting_ticket_label: Any,
) -> tuple[Any, str, Any, str]:
    _scan_result, queue_result, autopilot_status, diag_result = run_cycle(**cycle_kwargs)
    if auto_pipeline_state is not None:
        update_auto_pipeline_state(
            auto_pipeline_state,
            queue_result,
            diag_result,
            autopilot_status,
        )
    waiting_ticket = _save_cycle_checkpoint(
        checkpoint_path=checkpoint_path,
        cycle=cycle,
        loop_state=loop_state,
        queue_result=queue_result,
        queue_loop_waiting_ticket_label=queue_loop_waiting_ticket_label,
        save_loop_checkpoint=save_loop_checkpoint,
    )
    return queue_result, waiting_ticket, diag_result, autopilot_status


def _finish_cycle(
    *,
    args: Any,
    project: Any,
    cycle: int,
    queue_result: Any,
    waiting_ticket: str,
    loop_state: Any,
    diag_result: Any,
    autopilot_status: str,
    autopilot_ide: str,
    correlation_id: str,
    handle_exit_conditions: Any,
    compute_cycle_sleep: Any,
    stdio_info: Any,
    sleep: Any,
) -> bool:
    effective_sleep = compute_cycle_sleep(args, loop_state, queue_result, autopilot_status)
    stop_reason = _cycle_stop_reason(args, queue_result, cycle)
    _emit_cycle_summary(
        args=args,
        project=project,
        cycle=cycle,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        loop_state=loop_state,
        diag_result=diag_result,
        autopilot_status=autopilot_status,
        effective_sleep=effective_sleep,
        stdio_info=stdio_info,
    )
    _emit_idle_no_ticket_warning(
        args=args,
        project=project,
        queue_status=str(getattr(queue_result, "last_status", "") or ""),
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
    )
    _log_operator_next_steps(
        args=args,
        project=project,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        effective_sleep=effective_sleep,
        loop_state=loop_state,
        stop_reason=stop_reason,
        stdio_info=stdio_info,
        autopilot_ide=autopilot_ide,
    )
    _emit_structured_report(
        args=args,
        cycle=cycle,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        loop_state=loop_state,
        diag_result=diag_result,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        effective_sleep=effective_sleep,
    )
    if handle_exit_conditions(args, queue_result, cycle, correlation_id):
        return True

    if effective_sleep > 0:
        sleep(effective_sleep)
    return False


def run_autonomous_cycle(
    *,
    cycle: int,
    args: Any,
    project: Any,
    client: Any,
    daemon: Any,
    thread: Any,
    socket_path: Any,
    autopilot_socket_observed_at_boot: bool,
    queue_name: str | None,
    enable_scan: bool,
    autopilot_ide: str,
    loop_state: Any,
    checkpoint_path: Any,
    diagnostic_state_dir: Any,
    wup_process: Any | None,
    correlation_id: str,
    auto_pipeline_state: Any | None,
    restart_daemon_if_needed: Any,
    select_and_log_cycle_profile: Any,
    resolve_effective_cycle_flags: Any,
    build_cycle_run_kwargs: Any,
    run_cycle: Any,
    update_auto_pipeline_state: Any,
    save_loop_checkpoint: Any,
    queue_loop_waiting_ticket_label: Any,
    handle_exit_conditions: Any,
    compute_cycle_sleep: Any,
    stdio_info: Any,
    sleep: Any,
) -> bool:
    """Run one autonomous cycle and return True when the loop should exit."""
    _print_cycle_header(args, cycle)
    cycle_kwargs = _prepare_cycle_run(
        args=args,
        project=project,
        client=client,
        daemon=daemon,
        thread=thread,
        socket_path=socket_path,
        autopilot_socket_observed_at_boot=autopilot_socket_observed_at_boot,
        queue_name=queue_name,
        enable_scan=enable_scan,
        autopilot_ide=autopilot_ide,
        loop_state=loop_state,
        diagnostic_state_dir=diagnostic_state_dir,
        wup_process=wup_process,
        correlation_id=correlation_id,
        auto_pipeline_state=auto_pipeline_state,
        cycle=cycle,
        restart_daemon_if_needed=restart_daemon_if_needed,
        select_and_log_cycle_profile=select_and_log_cycle_profile,
        resolve_effective_cycle_flags=resolve_effective_cycle_flags,
        build_cycle_run_kwargs=build_cycle_run_kwargs,
    )
    queue_result, waiting_ticket, diag_result, autopilot_status = _run_cycle_and_checkpoint(
        cycle_kwargs=cycle_kwargs,
        cycle=cycle,
        loop_state=loop_state,
        checkpoint_path=checkpoint_path,
        auto_pipeline_state=auto_pipeline_state,
        run_cycle=run_cycle,
        update_auto_pipeline_state=update_auto_pipeline_state,
        queue_loop_waiting_ticket_label=queue_loop_waiting_ticket_label,
        save_loop_checkpoint=save_loop_checkpoint,
    )
    return _finish_cycle(
        args=args,
        project=project,
        cycle=cycle,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        loop_state=loop_state,
        diag_result=diag_result,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        correlation_id=correlation_id,
        handle_exit_conditions=handle_exit_conditions,
        compute_cycle_sleep=compute_cycle_sleep,
        stdio_info=stdio_info,
        sleep=sleep,
    )


__all__ = [
    "handle_cycle_exit_conditions",
    "run_autonomous_cycle",
]
