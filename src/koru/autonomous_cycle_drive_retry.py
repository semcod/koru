import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_chat_activity import _inject_reflection_summary_into_prompt
from koru.autonomous_cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomous_drive_retry_policy import _handle_failed_drive_attempt
from koru.autonomy.env import (
    allow_gillm_autopilot_fallback as _allow_gillm_autopilot_fallback,
)
from koru.autonomy.env import (
    allow_keyboard_autopilot_fallback as _allow_keyboard_autopilot_fallback,
)
from koru.autonomy.env import (
    env_truthy,
)
from koru.autonomy.env import (
    plugin_required_for_ide as _plugin_required_for_ide,
)
from koru.autonomy.env import (
    prefer_keyboard_autopilot as _prefer_keyboard_autopilot,
)
from koru.autonomy.ide_work import extract_ticket_id_from_text, resolve_idle_drive_prompt
from koru.autonomy.policy_decision import AutopilotPolicyDecision
from koru.autonomy.prompts import PromptDecision, build_prompt
from koru.autonomy.state import AutoloopState
from koru.decision_engine import (
    EnvironmentDecisionEngine,
    build_decision_engine,
)
from koru.queue import QueueLoopResult
from koru.queue import run_process as _run_process
from koruide.ide import normalize_ide_id as _normalize_ide_id
from koruide.ide import supports_vscode_extension_plugin as _supports_vscode_extension_plugin


def _max_drive_retries() -> int:
    """Read ``KORU_AUTOPILOT_DRIVE_MAX_RETRIES`` (default 3, was 5 historically).

    Three attempts handles the common transient case (focus race, plugin
    cold-start) without wasting 25s on identical failures when the issue is
    persistent (chat panel closed, plugin still loading old code).
    """
    raw = os.environ.get("KORU_AUTOPILOT_DRIVE_MAX_RETRIES", "").strip()
    if not raw:
        return 3
    try:
        value = int(raw)
    except ValueError:
        return 3
    return max(1, min(value, 10))


def _drive_failure_signature(reply: dict[str, Any]) -> str:
    """Stable signature for de-duplicating repeated retry attempts.

    The autonomous loop used to retry up to 5 times with a 5s sleep even when
    every reply carried the *same* failure reason (e.g. ``chat input is not
    focused/open``). That wasted 25s per cycle and spammed the operator with
    identical red banners. We collapse retries by hashing the most
    discriminating fields and breaking the loop as soon as the same signature
    appears twice in a row.
    """
    msg = str(reply.get("message") or "").strip().lower()
    verification = str(reply.get("verification") or "").strip().lower()
    reason = str(reply.get("reason") or "").strip().lower()
    return f"{verification}|{reason}|{msg[:200]}"


def _active_decision_engine(project: Path, autopilot_ide: str) -> EnvironmentDecisionEngine:
    return build_decision_engine(project, ide=autopilot_ide)


_CLOSED_TICKET_STATUSES = frozenset({"done", "closed", "cancelled", "canceled", "failed"})


def _cycle_attr(name: str, fallback: Any) -> Any:
    from koru import autonomous_cycle as _cycle_mod

    return getattr(_cycle_mod, name, fallback)


def _ide_supports_vscode_plugin(autopilot_ide: str) -> bool:
    ide = _normalize_ide_id(autopilot_ide) or ""
    return _supports_vscode_extension_plugin(ide)


def _operator_forces_keyboard() -> bool:
    """User opted into keyboard/gillm fallback; do not override with strict plugin."""
    return (
        _allow_keyboard_autopilot_fallback()
        or _prefer_keyboard_autopilot()
        or _allow_gillm_autopilot_fallback()
    )


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


def _try_imgl_gui_fallback(
    prompt: str,
    *,
    submit: bool,
    ide: str,
    project: Path | None = None,
) -> dict[str, Any] | None:
    """Delegate to :func:`koru.autonomous._try_imgl_gui_fallback` (monkeypatch-friendly)."""
    from koru import autonomous as _autonomous_mod

    return _autonomous_mod._try_imgl_gui_fallback(
        prompt,
        submit=submit,
        ide=ide,
        project=project,
    )


def _try_gillm_gui_fallback(
    prompt: str,
    *,
    submit: bool,
    ide: str,
    project: Path | None = None,
) -> dict[str, Any] | None:
    """Delegate to :func:`koru.autonomous._try_gillm_gui_fallback` (monkeypatch-friendly)."""
    from koru import autonomous as _autonomous_mod

    return _autonomous_mod._try_gillm_gui_fallback(
        prompt,
        submit=submit,
        ide=ide,
        project=project,
    )


def _try_vdisplay_control_fallback(
    prompt: str,
    *,
    submit: bool,
    ide: str,
    project: Path | None = None,
    plugin_connected: bool = False,
) -> dict[str, Any] | None:
    from koru import autonomous as _autonomous_mod

    return _autonomous_mod._try_vdisplay_control_fallback(
        prompt,
        submit=submit,
        ide=ide,
        project=project,
        plugin_connected=plugin_connected,
    )


def _try_nlp2uri_focus_fallback(prompt: str, *, submit: bool, ide: str) -> dict[str, Any] | None:
    from koru import autonomous as _autonomous_mod

    return _autonomous_mod.try_nlp2uri_focus_fallback(prompt, submit=submit, ide=ide)


def _try_os_injector_fallback(prompt: str, *, submit: bool) -> dict[str, Any] | None:
    """Delegate to :func:`koru.autonomous._try_os_injector_fallback` (monkeypatch-friendly)."""
    from koru import autonomous as _autonomous_mod

    return _autonomous_mod._try_os_injector_fallback(prompt, submit=submit)


def _try_nlp2uri_ide_control(
    prompt: str,
    *,
    submit: bool,
    ide: str,
    client: Any,
    project: Path | None = None,
) -> dict[str, Any] | None:
    """Delegate to :func:`koru.autonomous._try_nlp2uri_ide_control` (monkeypatch-friendly)."""
    from koru import autonomous as _autonomous_mod

    return _autonomous_mod._try_nlp2uri_ide_control(
        prompt,
        submit=submit,
        ide=ide,
        client=client,
        project=project,
    )


def _skip_closed_waiting_ticket_enabled() -> bool:
    """Guard stale ``waiting_input`` redrives when the ticket is already closed."""
    return env_truthy("KORU_AUTOPILOT_SKIP_CLOSED_WAITING_TICKET", True)


def _resolve_waiting_ticket_id(queue_result: QueueLoopResult) -> str:
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    if waiting_ticket and waiting_ticket != "-":
        return waiting_ticket
    raw = str(getattr(queue_result, "last_ticket_id", "") or "").strip()
    return raw


def _planfile_ticket_status(project: Path, ticket_id: str) -> str | None:
    ticket = ticket_id.strip()
    if not ticket:
        return None
    try:
        proc = _run_process(
            ["planfile", "ticket", "show", ticket, "--format", "json"],
            project,
        )
    except (OSError, TimeoutError, RuntimeError):
        return None
    if proc.returncode != 0:
        return None
    raw = str(proc.stdout or "").strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    status = str(payload.get("status") or "").strip().lower()
    if status:
        return status
    return None


def _waiting_ticket_is_closed(project: Path, ticket_id: str) -> bool:
    status = _planfile_ticket_status(project, ticket_id)
    return bool(status and status in _CLOSED_TICKET_STATUSES)


def _resolve_autopilot_drive_decision(
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    *,
    drive_prompt: str,
    autopilot_action: str,
) -> tuple[Any, str | None]:
    waiting_ticket_id = _resolve_waiting_ticket_id(queue_result)
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
    if (
        queue_result.last_status == "waiting_input"
        and waiting_ticket_id
        and _skip_closed_waiting_ticket_enabled()
        and _waiting_ticket_is_closed(project, waiting_ticket_id)
    ):
        return (
            PromptDecision(
                prompt="",
                kind="drive_prompt",
                skip=True,
                skip_reason="waiting_ticket_closed",
            ),
            idle_prompt_kind,
        )
    build_prompt_fn = _cycle_attr("build_prompt", build_prompt)
    decision = build_prompt_fn(
        queue_status=queue_result.last_status,
        last_message=getattr(queue_result, "last_message", "") or "",
        waiting_ticket_id=waiting_ticket_id or None,
        drive_prompt=effective_drive_prompt,
        autopilot_action=autopilot_action,
        stagnation_streak=state.stagnation_streak,
    )
    decision = _inject_reflection_summary_into_prompt(state, queue_result, decision)
    return decision, idle_prompt_kind


def _invoke_client_autopilot_drive(
    client: Any,
    *,
    prompt: str,
    submit: bool,
    autopilot_ide: str,
    require_plugin: bool,
    strategy_hint: str | None = None,
    project: Path | None = None,
) -> tuple[dict[str, Any], bool]:
    drive_kwargs: dict[str, Any] = {
        "submit": submit,
        "ide": autopilot_ide,
        "require_plugin": require_plugin,
    }
    if strategy_hint:
        drive_kwargs["strategy_hint"] = strategy_hint
    from koru.autonomous_cycle_gate import effective_ide_control_submit

    drive_submit = effective_ide_control_submit(submit=submit, ide=autopilot_ide)
    drive_kwargs["submit"] = drive_submit
    nlp2uri = _try_nlp2uri_ide_control(
        prompt,
        submit=drive_submit,
        ide=autopilot_ide,
        client=client,
        project=project,
    )
    if nlp2uri is not None:
        if nlp2uri.get("ok"):
            return nlp2uri, True
        if require_plugin:
            return nlp2uri, False
    if not require_plugin:
        from koru.integrations.imgl_client import imgl_prefer_before_keyboard

        if imgl_prefer_before_keyboard(autopilot_ide):
            imgl_first = _try_imgl_gui_fallback(
                prompt,
                submit=submit,
                ide=autopilot_ide,
                project=project,
            )
            if imgl_first is not None and imgl_first.get("ok"):
                return imgl_first, True
    reply = client.drive(prompt, **drive_kwargs)
    ok = bool(reply.get("ok", True))
    if ok or require_plugin:
        return reply, ok
    imgl = _try_imgl_gui_fallback(
        prompt,
        submit=submit,
        ide=autopilot_ide,
        project=project,
    )
    if imgl is not None and imgl.get("ok"):
        return imgl, True
    gillm = _try_gillm_gui_fallback(
        prompt,
        submit=submit,
        ide=autopilot_ide,
        project=project,
    )
    if gillm is not None and gillm.get("ok"):
        return gillm, True
    vdisplay = _try_vdisplay_control_fallback(
        prompt,
        submit=submit,
        ide=autopilot_ide,
        project=project,
        plugin_connected=bool(reply.get("ok")),
    )
    if vdisplay is not None and vdisplay.get("ok"):
        return vdisplay, True
    nlp2uri_focus = _try_nlp2uri_focus_fallback(prompt, submit=submit, ide=autopilot_ide)
    if nlp2uri_focus is not None and nlp2uri_focus.get("ok"):
        return nlp2uri_focus, True
    fallback = _try_os_injector_fallback(prompt, submit=submit)
    if fallback is not None:
        return fallback, bool(fallback.get("ok", True))
    if gillm is not None:
        return gillm, bool(gillm.get("ok", True))
    return reply, ok


def _waiting_ticket_closed_skip_result(
    queue_result: QueueLoopResult,
    idle_prompt_kind: str | None,
    skip_reason: str | None,
    _hp: Callable[..., Any],
) -> tuple[dict[str, Any], bool, str, str | None]:
    waiting_ticket = _resolve_waiting_ticket_id(queue_result) or "-"
    decision = AutopilotPolicyDecision.skip(
        "waiting_ticket_closed",
        because=f"ticket={waiting_ticket} is already closed in planfile",
        action_hint="refresh queue and pick next open ticket",
    )
    _hp(
        "- autopilot skipped (waiting_ticket_closed): "
        f"ticket {waiting_ticket} is already closed in planfile; "
        "suppressing stale waiting_input redrive.",
    )
    return (
        {
            "ok": False,
            "backend": None,
            "message": f"waiting ticket {waiting_ticket} is already closed; skip stale redrive",
            "prompt": "",
        },
        False,
        skip_reason or decision.status,
        idle_prompt_kind,
    )


def _idle_no_ticket_skip_result(
    project: Path,
    idle_prompt_kind: str | None,
    _hp: Callable[..., Any],
) -> tuple[dict[str, Any], bool, str, str | None]:
    from koru.autonomous_loop_runner import _dashboard_action_urls
    from koru.autonomy.ide_work import sprint_ticket_status_summary

    decision = AutopilotPolicyDecision.skip(
        "idle_no_ticket",
        because="queue idle and no open ticket in planfile",
        action_hint="run scan/discovery or create ticket",
    )
    urls = _dashboard_action_urls(project)
    _hp(
        "- autopilot skipped (idle_no_ticket): "
        "queue empty AND no open ticket in planfile → nothing to paste "
        "into the IDE chat. Drive is suppressed to avoid clobbering the "
        "user's input with stale prompts.",
    )
    _hp(f"  planfile snapshot: {sprint_ticket_status_summary(project)}")
    _hp(
        "  what koru auto will try next: "
        "(1) wait the configured sleep; (2) when queue stays idle, "
        "rerun `koru scan --apply` to look for new signals; "
        "(3) if scan finds signals already present as done tickets, "
        "they will be skipped as duplicates; use the quick action below "
        "to create a fresh discovery ticket immediately.",
    )
    _hp(
        "  quick actions: create discovery ticket "
        f"{urls['create_project_ticket_action']} ; tickets {urls['tickets']} ; "
        "force fresh scan command remains: "
        "`rm -rf project/ && KORU_SCAN_FORCE_RESCAN=1 koru auto`.",
    )
    return (
        {
            "ok": False,
            "backend": None,
            "message": "queue idle and no open ticket",
            "prompt": "",
        },
        False,
        decision.status,
        idle_prompt_kind,
    )


def _resolve_drive_plugin_requirement(client: Any, autopilot_ide: str) -> bool:
    require_plugin = _plugin_required_for_ide(autopilot_ide)
    if (
        not require_plugin
        and _ide_supports_vscode_plugin(autopilot_ide)
        and not _operator_forces_keyboard()
    ):
        plugin_live, _ = _client_has_usable_plugin(client, autopilot_ide)
        if plugin_live:
            return True
    return require_plugin


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


def _reply_needs_submit_retry(reply: dict[str, Any]) -> bool:
    """True when text was injected but the submit step did not complete.

    The VS Code-family plugin verifies host-key submits by probing whether the
    chat input was cleared. If that verification fails, a second drive can
    safely re-use the already pasted prompt: the plugin detects matching input
    and runs ``submit_existing`` instead of pasting again.
    """
    verification = str(reply.get("verification") or "").lower()
    if verification in {"submit_unverified", "submit_failed"}:
        return True
    if reply.get("submitted") is False and (
        reply.get("attempted_submit")
        or reply.get("winning_paste")
        or reply.get("submit_failure_reason")
    ):
        return True
    msg = str(reply.get("message") or "").lower()
    return "submit could not be verified" in msg or "submit failed" in msg


def _reply_requires_manual_chat_focus(reply: dict[str, Any]) -> bool:
    msg = str(reply.get("message") or "").lower()
    if "chat input is not focused/open" not in msg:
        return False
    diagnostics = reply.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return False
    candidates = diagnostics.get("focusOpenCandidates")
    return isinstance(candidates, list) and not candidates


def _run_drive_retry_loop(
    client: Any,
    *,
    prompt: str,
    submit: bool,
    autopilot_ide: str,
    require_plugin: bool,
    attempts: int,
    engine: EnvironmentDecisionEngine,
    strategy_hint: str | None = None,
    project: Path | None = None,
    _hp: Callable[..., Any],
) -> tuple[dict[str, Any], bool]:
    previous_signature: str | None = None
    for attempt in range(attempts):
        reply, ok = _invoke_client_autopilot_drive(
            client,
            prompt=prompt,
            submit=submit,
            autopilot_ide=autopilot_ide,
            require_plugin=require_plugin,
            strategy_hint=strategy_hint,
            project=project,
        )
        if ok:
            break
        signature = engine.llm_strategy.failure_signature(reply)
        if previous_signature is not None and signature == previous_signature:
            _hp(
                "  autopilot: aborting retry loop — identical failure repeated "
                f"(attempt {attempt + 1}/{attempts}, signature unchanged)",
            )
            break
        previous_signature = signature
        if not _handle_failed_drive_attempt(
            reply,
            attempt,
            attempts,
            engine=engine,
        ):
            break
    return reply, ok


def _execute_autopilot_drive(
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    client: Any,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    autopilot_action: str,
    _hp: Callable[..., Any],
) -> tuple[dict[str, Any], bool, str, str | None]:
    """Execute autopilot drive and return (reply, ok, decision_kind, idle_prompt_kind)."""
    decision, idle_prompt_kind = _resolve_autopilot_drive_decision(
        project,
        state,
        queue_result,
        drive_prompt=drive_prompt,
        autopilot_action=autopilot_action,
    )
    if decision.skip:
        return _waiting_ticket_closed_skip_result(
            queue_result,
            idle_prompt_kind,
            decision.skip_reason,
            _hp,
        )
    if idle_prompt_kind == "idle_no_ticket":
        return _idle_no_ticket_skip_result(project, idle_prompt_kind, _hp)
    state.last_driven_prompt = decision.prompt
    # Telemetry hook used by ``_skip_due_to_recent_chat_activity`` to decide
    # whether to apply the escalation-cooldown multiplier on the next cycle.
    state.last_driven_kind = decision.kind
    require_plugin = _resolve_drive_plugin_requirement(client, autopilot_ide)
    attempts = _max_drive_retries()
    engine = _active_decision_engine(project, autopilot_ide)
    from koru.autonomous_submit_strategy import consume_pending_submit_strategy_hint

    strategy_hint = consume_pending_submit_strategy_hint(state)
    if strategy_hint:
        _hp(f"  autopilot: submit strategy hint={strategy_hint}")
    reply, ok = _run_drive_retry_loop(
        client,
        prompt=decision.prompt,
        submit=submit,
        autopilot_ide=autopilot_ide,
        require_plugin=require_plugin,
        attempts=attempts,
        engine=engine,
        strategy_hint=strategy_hint,
        project=project,
        _hp=_hp,
    )

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
    _hp: Callable[..., Any],
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
        if decision_kind in {"idle_no_ticket", "waiting_ticket_closed"}:
            return
        elif _reply_requires_manual_chat_focus(reply):
            _hp(
                "  autopilot: skipped(manual_focus) "
                f"({reply.get('message', 'unknown error')}, kind={decision_kind})",
            )
        else:
            msg = reply.get("message", "unknown error")
            _hp(
                f"  autopilot: failed ({msg}, kind={decision_kind})",
            )
