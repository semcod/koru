import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomous_drive_retry_policy import _handle_failed_drive_attempt
from koru.autonomy.cycle.cycle_chat_activity import _inject_reflection_summary_into_prompt
from koru.autonomy.cycle.cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomy.drive_strategies import (
    DriveStrategy,
    DriveStrategyContext,
    execute_drive_strategies,
)
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


def _workspace_mismatch_override() -> bool:
    return os.environ.get("KORU_AUTOPILOT_ALLOW_WORKSPACE_MISMATCH", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _client_has_usable_plugin(
    client: Any,
    autopilot_ide: str,
    project: Path | None = None,
) -> tuple[bool, str]:
    """Return whether a daemon status has a live plugin usable for this IDE.

    When ``project`` is given, the plugin's workspaceFolders must cover it:
    driving a plugin whose IDE window has a *different* project open sends
    prompts into a foreign chat (2026-07-03 cross-project incident). Override
    with KORU_AUTOPILOT_ALLOW_WORKSPACE_MISMATCH=1.
    """
    from koru.autonomy.operator.operator_plugin import plugin_status_decision

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

    ok, reason = plugin_status_decision(status, autopilot_ide)
    if not ok:
        return ok, reason
    if project is not None and not _workspace_mismatch_override():
        conflict = _plugin_workspace_conflict(status, autopilot_ide, project)
        if conflict:
            return False, (
                f"workspace mismatch: {conflict} — prompts would land in a "
                "foreign IDE window; open the project in the IDE and run "
                "'koru: Connect autopilot daemon' "
                "(override: KORU_AUTOPILOT_ALLOW_WORKSPACE_MISMATCH=1)"
            )
    return True, ""


def _plugin_workspace_conflict(
    status: Any,
    autopilot_ide: str,
    project: Path,
) -> str | None:
    """A *positive* workspace conflict: folders reported and none covers project.

    Plugins that do not report ``workspaceFolders`` (older builds, test fakes)
    are not treated as conflicting — readiness separately surfaces the missing
    info; the drive gate only blocks when we know prompts would land in a
    window with a different project open (2026-07-03 cross-project incident).
    """
    plugins = status.get("plugins") if isinstance(status, dict) else None
    if not isinstance(plugins, list):
        return None
    wanted = (autopilot_ide or "").strip().lower()
    project_path = str(project.resolve()).rstrip("/")
    seen_folders: list[str] = []
    for row in plugins:
        if not isinstance(row, dict):
            continue
        ide = str(row.get("ide") or "").strip().lower()
        if wanted not in ("", "auto") and ide != wanted:
            continue
        folders = row.get("workspaceFolders")
        if not isinstance(folders, list) or not folders:
            continue  # unknown workspace — not a conflict
        normalized = [str(folder).rstrip("/") for folder in folders if str(folder).strip()]
        for folder in normalized:
            if (
                folder == project_path
                or project_path.startswith(folder + "/")
                or folder.startswith(project_path + "/")
            ):
                return None  # covered
        seen_folders = normalized
    if seen_folders:
        return (
            f"plugin workspaceFolders {seen_folders!r} do not include "
            f"project root ({project_path})"
        )
    return None


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
    from koru.autonomy.cycle.cycle_gate import try_nlp2uri_focus_fallback

    return try_nlp2uri_focus_fallback(prompt, submit=submit, ide=ide)


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


def _waiting_ticket_is_missing(project: Path, ticket_id: str) -> bool:
    """True only when planfile definitively says the ticket does not exist.

    Probe failures (planfile unavailable, timeout) return False — a transient
    outage must not drop a legitimate ticket id from prompts.
    """
    ticket = ticket_id.strip()
    if not ticket:
        return False
    try:
        proc = _run_process(
            ["planfile", "ticket", "show", ticket, "--format", "json"],
            project,
        )
    except (OSError, TimeoutError, RuntimeError):
        return False
    if proc.returncode == 0:
        return False
    output = f"{proc.stdout}\n{proc.stderr}".lower()
    return "not found" in output


def _resolve_autopilot_drive_decision(
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    *,
    drive_prompt: str,
    autopilot_action: str,
    queue_name: str | None = None,
) -> tuple[Any, str | None]:
    waiting_ticket_id = _resolve_waiting_ticket_id(queue_result)
    # A ghost id (2026-07-03: escalation named nonexistent PLF-001) poisons
    # every downstream prompt — the driven LLM is told to implement and close
    # a ticket that does not exist. Drop it loudly.
    if waiting_ticket_id and _waiting_ticket_is_missing(project, waiting_ticket_id):
        import sys as _sys

        print(
            f"[koru] waiting ticket {waiting_ticket_id!r} not found in planfile — "
            "dropping ghost id from autopilot prompts",
            file=_sys.stderr,
        )
        waiting_ticket_id = ""
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
            queue_name=queue_name,
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


def _build_drive_kwargs(
    *,
    submit: bool,
    autopilot_ide: str,
    require_plugin: bool,
    strategy_hint: str | None = None,
) -> dict[str, Any]:
    from koru.autonomy.cycle.cycle_gate import effective_ide_control_submit

    drive_submit = effective_ide_control_submit(submit=submit, ide=autopilot_ide)
    drive_kwargs: dict[str, Any] = {
        "submit": drive_submit,
        "ide": autopilot_ide,
        "require_plugin": require_plugin,
    }
    if strategy_hint:
        drive_kwargs["strategy_hint"] = strategy_hint
    return drive_kwargs


def _pre_drive_fallback(
    client: Any,
    *,
    prompt: str,
    submit: bool,
    autopilot_ide: str,
    require_plugin: bool,
    project: Path | None = None,
) -> tuple[dict[str, Any], bool] | None:
    context = DriveStrategyContext(
        client=client,
        prompt=prompt,
        submit=submit,
        autopilot_ide=autopilot_ide,
        require_plugin=require_plugin,
        project=project,
    )
    strategies = [
        DriveStrategy(
            "nlp2uri_control",
            lambda ctx: _try_nlp2uri_ide_control(
                ctx.prompt,
                submit=ctx.submit,
                ide=ctx.autopilot_ide,
                client=ctx.client,
                project=ctx.project,
            ),
            return_on_failure=require_plugin,
        )
    ]
    if not require_plugin:
        strategies.append(
            DriveStrategy(
                "vdisplay",
                lambda ctx: _try_vdisplay_control_fallback(
                    ctx.prompt,
                    submit=ctx.submit,
                    ide=ctx.autopilot_ide,
                    project=ctx.project,
                    plugin_connected=False,
                ),
            )
        )
        from koru.integrations.imgl_client import imgl_prefer_before_keyboard

        if imgl_prefer_before_keyboard(autopilot_ide):
            strategies.append(
                DriveStrategy(
                    "imgl_pre_keyboard",
                    lambda ctx: _try_imgl_gui_fallback(
                        ctx.prompt,
                        submit=ctx.submit,
                        ide=ctx.autopilot_ide,
                        project=ctx.project,
                    ),
                )
            )
    return execute_drive_strategies(strategies, context)


def _post_drive_fallback_chain(
    *,
    prompt: str,
    submit: bool,
    autopilot_ide: str,
    reply: dict[str, Any],
    project: Path | None = None,
) -> tuple[dict[str, Any], bool] | None:
    context = DriveStrategyContext(
        client=None,
        prompt=prompt,
        submit=submit,
        autopilot_ide=autopilot_ide,
        require_plugin=False,
        project=project,
        plugin_reply=reply,
    )
    return execute_drive_strategies(
        [
            DriveStrategy(
                "vdisplay",
                lambda ctx: _try_vdisplay_control_fallback(
                    ctx.prompt,
                    submit=ctx.submit,
                    ide=ctx.autopilot_ide,
                    project=ctx.project,
                    plugin_connected=bool((ctx.plugin_reply or {}).get("ok")),
                ),
            ),
            DriveStrategy(
                "imgl",
                lambda ctx: _try_imgl_gui_fallback(
                    ctx.prompt,
                    submit=ctx.submit,
                    ide=ctx.autopilot_ide,
                    project=ctx.project,
                ),
            ),
            DriveStrategy(
                "gillm",
                lambda ctx: _try_gillm_gui_fallback(
                    ctx.prompt,
                    submit=ctx.submit,
                    ide=ctx.autopilot_ide,
                    project=ctx.project,
                ),
                keep_failure=True,
            ),
            DriveStrategy(
                "nlp2uri_focus",
                lambda ctx: _try_nlp2uri_focus_fallback(
                    ctx.prompt,
                    submit=ctx.submit,
                    ide=ctx.autopilot_ide,
                ),
            ),
            DriveStrategy(
                "os_injector",
                lambda ctx: _try_os_injector_fallback(ctx.prompt, submit=ctx.submit),
                return_on_failure=True,
            ),
        ],
        context,
    )


def _drive_shell_client(
    client_id: str,
    *,
    prompt: str,
    project: Path | None,
) -> tuple[dict[str, Any], bool]:
    """Drive a vendor CLI (claude-code, aider, codex, …) headlessly via tillm."""
    from koru.tillm_bridge import drive_shell_chat

    try:
        reply = drive_shell_chat(
            client_id=client_id,
            project=project or Path.cwd(),
            prompt=prompt,
            execute=True,
            model=os.environ.get("KORU_TILLM_MODEL", "").strip() or None,
            execute_profile=os.environ.get("KORU_TILLM_EXECUTE_PROFILE", "").strip()
            or "default",
        )
    except Exception as exc:
        reply = {
            "ok": False,
            "backend": "tillm_shell",
            "client_id": client_id,
            "message": str(exc),
            "type": "error",
        }
    reply.setdefault("prompt", prompt)
    return reply, bool(reply.get("ok"))


def _shell_drive_editor_rescue(
    reply: dict[str, Any],
    *,
    client_id: str,
    prompt: str,
    submit: bool,
    project: Path | None,
) -> tuple[dict[str, Any], bool] | None:
    """Cross-lane rescue: the tillm CLI cannot run but an editor IDE is open.

    Engages only when the shell client is genuinely unavailable (tillm missing
    or the vendor CLI not on PATH) — real execution errors from a working CLI
    are never masked — and only when a running editor gives the GUI fallback
    chain something to target.
    """
    from koru.tillm_bridge import shell_agent_available

    if shell_agent_available(client_id):
        return None
    try:
        from koruide.ide import detect_running_ides

        running = detect_running_ides()
    except Exception as exc:  # noqa: BLE001 — rescue is optional, but say why it was skipped
        import sys

        print(
            f"[koru] editor-rescue skipped: IDE detection failed: {exc}",
            file=sys.stderr,
        )
        return None
    if not running:
        return None
    result = _post_drive_fallback_chain(
        prompt=prompt,
        submit=submit,
        autopilot_ide=running[0].id,
        reply=reply,
        project=project,
    )
    if result is None:
        return None
    rescued, ok = result
    rescued.setdefault("shell_client_rescued_from", client_id)
    return rescued, ok


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
    from koru.tillm_bridge import shell_drive_client_id

    shell_client = shell_drive_client_id(autopilot_ide)
    if shell_client:
        reply, ok = _drive_shell_client(shell_client, prompt=prompt, project=project)
        if ok:
            return reply, ok
        rescue = _shell_drive_editor_rescue(
            reply,
            client_id=shell_client,
            prompt=prompt,
            submit=submit,
            project=project,
        )
        if rescue is not None:
            return rescue
        return reply, ok

    drive_kwargs = _build_drive_kwargs(
        submit=submit,
        autopilot_ide=autopilot_ide,
        require_plugin=require_plugin,
        strategy_hint=strategy_hint,
    )

    pre = _pre_drive_fallback(
        client,
        prompt=prompt,
        submit=drive_kwargs["submit"],
        autopilot_ide=autopilot_ide,
        require_plugin=require_plugin,
        project=project,
    )
    if pre is not None:
        return pre

    reply = client.drive(prompt, **drive_kwargs)
    ok = bool(reply.get("ok", True))
    if ok or require_plugin:
        return reply, ok

    post = _post_drive_fallback_chain(
        prompt=prompt,
        submit=submit,
        autopilot_ide=autopilot_ide,
        reply=reply,
        project=project,
    )
    if post is not None:
        return post

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
    from koru.autonomy.operator.operator_loop_runner import _dashboard_action_urls
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
    queue_name: str | None = None,
) -> tuple[dict[str, Any], bool, str, str | None]:
    """Execute autopilot drive and return (reply, ok, decision_kind, idle_prompt_kind)."""
    decision, idle_prompt_kind = _resolve_autopilot_drive_decision(
        project,
        state,
        queue_result,
        drive_prompt=drive_prompt,
        autopilot_action=autopilot_action,
        queue_name=queue_name,
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
