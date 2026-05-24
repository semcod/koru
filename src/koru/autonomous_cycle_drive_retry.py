import time
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_chat_activity import _inject_reflection_summary_into_prompt
from koru.autonomous_cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomy.env import (
    allow_keyboard_autopilot_fallback as _allow_keyboard_autopilot_fallback,
    plugin_required_for_ide as _plugin_required_for_ide,
    prefer_keyboard_autopilot as _prefer_keyboard_autopilot,
)
from koru.autonomy.ide_work import extract_ticket_id_from_text, resolve_idle_drive_prompt
from koru.autonomy.prompts import build_prompt
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.queue import run_process as _run_process
from koruide.ide import normalize_ide_id as _normalize_ide_id
from koruide.ide import supports_vscode_extension_plugin as _supports_vscode_extension_plugin


def _cycle_attr(name: str, fallback: Any) -> Any:
    from koru import autonomous_cycle as _cycle_mod

    return getattr(_cycle_mod, name, fallback)


def _ide_supports_vscode_plugin(autopilot_ide: str) -> bool:
    ide = _normalize_ide_id(autopilot_ide) or ""
    return _supports_vscode_extension_plugin(ide)


def _operator_forces_keyboard() -> bool:
    """User explicitly demanded keyboard/OS-injector path; do not override."""
    return _allow_keyboard_autopilot_fallback() or _prefer_keyboard_autopilot()


def _client_has_usable_plugin(client: Any, autopilot_ide: str) -> tuple[bool, str]:
    """Return whether a daemon status has a live plugin usable for this IDE."""
    from koru.autonomous_plugin import plugin_status_decision

    status_fn = getattr(client, "status", None)
    if not callable(status_fn):
        return True, ""
    try:
        status = status_fn()
    except (OSError, TimeoutError, RuntimeError) as exc:
        return False, f"daemon status unavailable: {exc}"
    
    plugins = status.get("plugins")
    if plugins is None:
        return True, ""
    
    return plugin_status_decision(status, autopilot_ide)


def _try_os_injector_fallback(prompt: str, *, submit: bool) -> dict[str, Any] | None:
    """Delegate to :func:`koru.autonomous._try_os_injector_fallback` (monkeypatch-friendly)."""
    from koru import autonomous as _autonomous_mod

    return _autonomous_mod._try_os_injector_fallback(prompt, submit=submit)


def _resolve_autopilot_drive_decision(
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    *,
    drive_prompt: str,
    autopilot_action: str,
) -> tuple[Any, str | None]:
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    effective_drive_prompt = drive_prompt
    idle_prompt_kind: str | None = None
    if queue_result.last_status == "idle":
        resolve_idle_prompt = _cycle_attr(
            "resolve_idle_drive_prompt",
            resolve_idle_drive_prompt,
        )
        effective_drive_prompt, idle_prompt_kind = resolve_idle_prompt(
            project,
            drive_prompt=drive_prompt,
            runner=_cycle_attr("_run_process", _run_process),
        )
    build_prompt_fn = _cycle_attr("build_prompt", build_prompt)
    decision = build_prompt_fn(
        queue_status=queue_result.last_status,
        last_message=getattr(queue_result, "last_message", "") or "",
        waiting_ticket_id=(
            waiting_ticket
            if waiting_ticket != "-"
            else getattr(queue_result, "last_ticket_id", None)
        ),
        drive_prompt=effective_drive_prompt,
        autopilot_action=autopilot_action,
        stagnation_streak=state.stagnation_streak,
    )
    decision = _inject_reflection_summary_into_prompt(state, queue_result, decision)
    return decision, idle_prompt_kind


def _drive_autopilot_once(
    client: Any,
    *,
    prompt: str,
    submit: bool,
    autopilot_ide: str,
    require_plugin: bool,
) -> tuple[dict[str, Any], bool]:
    reply = client.drive(
        prompt,
        submit=submit,
        ide=autopilot_ide,
        require_plugin=require_plugin,
    )
    ok = bool(reply.get("ok", True))
    if ok or require_plugin:
        return reply, ok
    fallback = _try_os_injector_fallback(prompt, submit=submit)
    if fallback is None:
        return reply, ok
    return fallback, bool(fallback.get("ok", True))


def _reply_missing_autopilot_plugin(reply: dict[str, Any]) -> bool:
    return "no connected autopilot plugin" in str(reply.get("message") or "").lower()


def _reply_chat_input_busy(reply: dict[str, Any]) -> bool:
    """``True`` when plugin (≥0.1.50) reported the chat input is non-empty.

    The plugin acks with ``verification="input_busy"`` and
    ``reason="chat_input_not_empty"`` when its pre-paste probe finds
    un-submitted text in the chat textarea — typically the user is mid-reply
    or the IDE-side LLM left a clarifying question. The autonomous loop
    treats this exactly like a successful skip-with-cooldown so it does not
    keep retrying every cycle.
    """
    if str(reply.get("verification") or "").lower() == "input_busy":
        return True
    return str(reply.get("reason") or "").lower() == "chat_input_not_empty"


def _reply_needs_focus_retry(reply: dict[str, Any]) -> bool:
    msg = str(reply.get("message") or "").lower()
    return "focus" in msg


def _reply_needs_plugin_retry(reply: dict[str, Any]) -> bool:
    msg = str(reply.get("message") or "").lower()
    if "no connected autopilot plugin" in msg:
        return False
    if "focus" in msg:
        return False
    return (
        "plugin_error" in msg
        or "connection" in msg
        or "verification" in msg
        or "connected" in msg
        or str(reply.get("verification") or "").lower() == "plugin_error"
    )


def _reply_requires_manual_chat_focus(reply: dict[str, Any]) -> bool:
    msg = str(reply.get("message") or "").lower()
    if "chat input is not focused/open" not in msg:
        return False
    diagnostics = reply.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return False
    candidates = diagnostics.get("focusOpenCandidates")
    return isinstance(candidates, list) and not candidates


def _format_autopilot_failure_details(reply: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    message = str(reply.get("message") or "").strip()
    if message:
        lines.append(f"Plugin message: {message}")
    diagnostics = reply.get("diagnostics")
    if isinstance(diagnostics, dict):
        for key in ("ide", "appName", "logPath", "probeLadder", "cacheFocusOpen"):
            if key in diagnostics:
                lines.append(f"{key}: {diagnostics[key]}")
        candidates = diagnostics.get("focusOpenCandidates")
        if isinstance(candidates, list):
            preview = ", ".join(str(item) for item in candidates[:8])
            if len(candidates) > 8:
                preview += f", ... (+{len(candidates) - 8})"
            lines.append(f"focusOpenCandidates: {preview or '(none)'}")
        rejected = diagnostics.get("rejected")
        if isinstance(rejected, list) and rejected:
            lines.append(f"lastRejected: {rejected[-1]}")
    elif reply.get("details"):
        lines.append(f"Details: {reply['details']}")
    return lines


def _warn_autopilot_focus_retry(attempt: int, attempts: int, reply: dict[str, Any] | None = None) -> None:
    print("\033[1;31m")  # bold red
    print("================================================================================")
    print("[AUTOPILOT FOCUS ERROR] Please place your cursor inside the IDE chat input!")
    print("Make sure the cursor is blinking inside the chat input field.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{attempts})")
    print("================================================================================")
    print("\033[0m")  # reset colors


def _warn_autopilot_manual_focus_required(reply: dict[str, Any] | None = None) -> None:
    from koru.activity_log import activity

    print("\033[1;31m")  # bold red
    print("================================================================================")
    print("[AUTOPILOT FOCUS REQUIRED] Please place your cursor inside the IDE chat input.")
    print("No focus-open command is available, so Koru will not retry this drive automatically.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print("================================================================================")
    print("\033[0m")  # reset colors
    activity(
        "CHAT",
        "manual focus required; no automatic retry",
        data={"reply": reply or {}},
    )


def _warn_autopilot_plugin_retry(attempt: int, attempts: int, reply: dict[str, Any] | None = None) -> None:
    print("\033[1;33m")  # bold yellow
    print("================================================================================")
    print("[AUTOPILOT PLUGIN RETRY] Plugin send did not succeed yet.")
    print("This is usually transient in Windsurf; Koru will retry automatically.")
    if reply:
        for line in _format_autopilot_failure_details(reply):
            print(line)
    print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{attempts})")
    print("================================================================================")
    print("\033[0m")  # reset colors


def _execute_autopilot_drive(
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    client: Any,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    autopilot_action: str,
    _hp: callable,
) -> tuple[dict[str, Any], bool, str, str | None]:
    """Execute autopilot drive and return (reply, ok, decision_kind, idle_prompt_kind)."""
    decision, idle_prompt_kind = _resolve_autopilot_drive_decision(
        project,
        state,
        queue_result,
        drive_prompt=drive_prompt,
        autopilot_action=autopilot_action,
    )
    if idle_prompt_kind == "idle_no_ticket":
        _hp("- autopilot skipped (idle_no_ticket)")
        return (
            {
                "ok": False,
                "backend": None,
                "message": "queue idle and no open ticket",
                "prompt": "",
            },
            False,
            "idle_no_ticket",
            idle_prompt_kind,
        )
    state.last_driven_prompt = decision.prompt
    # Telemetry hook used by ``_skip_due_to_recent_chat_activity`` to decide
    # whether to apply the escalation-cooldown multiplier on the next cycle.
    state.last_driven_kind = decision.kind
    require_plugin = _plugin_required_for_ide(autopilot_ide)
    # When the plugin is actually connected for a VS Code-family IDE, demand a
    # plugin ack even if the keyboard/OS-injector fallback policy is otherwise
    # active. Otherwise a busy IDE chat causes the daemon to switch to an
    # OS-injector blind shot (often into the wrong window on Wayland).
    if (
        not require_plugin
        and _ide_supports_vscode_plugin(autopilot_ide)
        and not _operator_forces_keyboard()
    ):
        plugin_live, _ = _client_has_usable_plugin(client, autopilot_ide)
        if plugin_live:
            require_plugin = True
    attempts = 5
    for attempt in range(attempts):
        reply, ok = _drive_autopilot_once(
            client,
            prompt=decision.prompt,
            submit=submit,
            autopilot_ide=autopilot_ide,
            require_plugin=require_plugin,
        )
        if ok:
            break
        if _reply_missing_autopilot_plugin(reply):
            break
        if _reply_chat_input_busy(reply):
            # Plugin already declined to paste; do not retry within this
            # cycle — the cooldown path on the next cycle will hold us off
            # until the user has cleared their pending chat input.
            break
        if _reply_requires_manual_chat_focus(reply):
            _warn_autopilot_manual_focus_required(reply)
            break
        if _reply_needs_focus_retry(reply) and attempt < attempts - 1:
            _warn_autopilot_focus_retry(attempt, attempts, reply)
            time.sleep(5)
        elif _reply_needs_plugin_retry(reply) and attempt < attempts - 1:
            _warn_autopilot_plugin_retry(attempt, attempts, reply)
            time.sleep(5)
        else:
            break

    return reply, ok, decision.kind, idle_prompt_kind


def _update_autopilot_state(
    state: AutoloopState,
    ok: bool,
    decision_kind: str,
    autopilot_drive_kind: str,
    decision_prompt: str,
) -> None:
    """Update autoloop state based on autopilot result."""
    if ok and autopilot_drive_kind == "idle_ticket_prompt":
        ticket_id = extract_ticket_id_from_text(decision_prompt)
        if ticket_id:
            state.pending_ide_verify_id = ticket_id
    if ok and decision_kind == "escalation_prompt":
        state.stagnation_streak = 0
        state.previous_signature = ""


def _log_autopilot_result(
    ok: bool,
    queue_result: QueueLoopResult,
    autopilot_ide: str,
    decision_kind: str,
    reply: dict[str, Any],
    _hp: callable,
) -> None:
    """Log autopilot result."""
    if ok:
        backend = reply.get("backend", "?")
        verification = reply.get("verification", "-")
        if backend in (None, "?") and verification == "-" and not reply.get("event"):
            _hp(
                "  autopilot: no confirmed IDE delivery "
                f"(kind={decision_kind}, queue_status={queue_result.last_status})",
            )
            return
        extra = ""
        if verification != "-":
            extra = f", verification={verification}"
        if reply.get("winning_submit"):
            extra += f", submit={reply['winning_submit']}"
        if reply.get("event"):
            extra += f", event={reply['event']}"
        if decision_kind == "ticket_prompt":
            waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
            _hp(
                "  autopilot: ok (ticket="
                f"{waiting_ticket}, ide={autopilot_ide}, "
                f"backend={backend}, kind={decision_kind}{extra})",
            )
        else:
            _hp(
                "  autopilot: ok "
                f"(ide={autopilot_ide}, backend={backend}, kind={decision_kind}{extra})",
            )
    else:
        if decision_kind == "idle_no_ticket":
            _hp("  autopilot: skipped(idle_no_ticket)")
        elif _reply_requires_manual_chat_focus(reply):
            _hp(
                "  autopilot: skipped(manual_focus) "
                f"({reply.get('message', 'unknown error')}, kind={decision_kind})",
            )
        else:
            _hp(
                f"  autopilot: failed ({reply.get('message', 'unknown error')}, kind={decision_kind})",
            )
