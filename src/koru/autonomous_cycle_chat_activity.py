from __future__ import annotations

import os
import re
import subprocess
import time
from hashlib import sha1
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomy.prompts import PromptDecision
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.tasks import create_nl_task


def _cycle_attr(name: str, fallback: Any) -> Any:
    from koru import autonomous_cycle as _cycle_mod

    return getattr(_cycle_mod, name, fallback)


def _autopilot_redrive_cooldown_seconds() -> float:
    """Operator-tunable cooldown (env: ``KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS``).

    Defaults to 300 s. The autopilot loop must NOT redrive the same
    ``llm-ready`` ticket prompt if a ``message.sent`` or ``message.received``
    event has been logged within this window — that means the IDE-side LLM
    is still working, or just answered, and a re-paste would clobber its
    output. Set to ``0`` (or negative) to disable the new behavior and
    restore the legacy "redrive every cycle" semantics.
    """
    raw = os.environ.get("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "").strip()
    if not raw:
        return 300.0
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 300.0


def _autopilot_escalation_cooldown_seconds(base_cooldown: float) -> float:
    """Cooldown applied when the LAST drive was an ``escalation_prompt``.

    Escalations ("Ticket X has been stuck in status 'waiting_input' for N
    cycles…") are explicit nudges aimed at an LLM that has likely already
    asked the user a clarifying question. Hammering the chat with another
    escalation every 30 s actively destroys the dialog: it concatenates new
    text on top of the user's pending reply or scrolls the LLM's question
    out of view. Use ``KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS`` (default
    1800 = 30 min) to give a real human / the IDE-side LLM enough time to
    converge before the next nudge. Falls back to ``base_cooldown`` when set
    to a value below it (cooldown can never shrink below the global one).
    """
    raw = os.environ.get("KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS", "").strip()
    if not raw:
        return max(base_cooldown, 1800.0)
    try:
        value = float(raw)
    except ValueError:
        return max(base_cooldown, 1800.0)
    return max(base_cooldown, max(0.0, value))


def _llm_reflection_summary_max_age_seconds() -> float:
    raw = os.environ.get("KORU_LLM_REFLECTION_SUMMARY_MAX_AGE_SECONDS", "").strip()
    if not raw:
        return 1800.0
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 1800.0


def _recent_llm_reflection_summary(state: AutoloopState) -> str:
    summary = str(getattr(state, "last_llm_reflection_summary", "") or "").strip()
    if not summary:
        return ""
    ts_raw = getattr(state, "last_llm_reflection_ts", 0.0)
    try:
        ts = float(ts_raw or 0.0)
    except (TypeError, ValueError):
        ts = 0.0
    if ts <= 0:
        return ""
    max_age = _llm_reflection_summary_max_age_seconds()
    if max_age > 0 and (time.time() - ts) > max_age:
        return ""
    return summary


def _llm_needs_input_ticket_enabled() -> bool:
    raw = os.environ.get("KORU_LLM_NEEDS_INPUT_TICKET", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _llm_needs_input_ticket_queue_name() -> str:
    raw = os.environ.get("KORU_LLM_NEEDS_INPUT_TICKET_QUEUE", "").strip()
    return raw or "operator"


def _llm_needs_input_ticket_priority() -> str:
    raw = os.environ.get("KORU_LLM_NEEDS_INPUT_TICKET_PRIORITY", "").strip()
    return raw or "high"


def _llm_needs_input_heuristic_enabled() -> bool:
    raw = os.environ.get("KORU_LLM_NEEDS_INPUT_HEURISTIC", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _chat_intake_ticket_enabled() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_CHAT_INTAKE_TICKET", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _waiting_ticket_has_chat_intake_label(
    project: Path,
    queue_result: QueueLoopResult,
) -> bool:
    try:
        from koru.autonomous_cycle_skip_conditions import _waiting_ticket_has_label
    except ImportError:
        return False
    return _waiting_ticket_has_label(project, queue_result, "autopilot-chat-intake")


def _normalize_prompt_text(text: str) -> str:
    return " ".join(str(text or "").split()).strip().lower()


def _looks_like_autopilot_generated_prompt(text: str) -> bool:
    normalized = _normalize_prompt_text(text)
    if not normalized:
        return False
    if normalized.startswith("ticket ") and " has been stuck in status " in normalized:
        return True
    if normalized.startswith("work on planfile ticket "):
        return True
    if "planfile ticket done " in normalized:
        return True
    if normalized.startswith("the queue is blocked on waiting_input"):
        return True
    return False


def _looks_like_explicit_intake_text(text: str) -> bool:
    raw = " ".join(str(text or "").split()).strip()
    if not raw:
        return False
    lowered = raw.lower()
    if lowered.startswith(("/", "./", "../", "~/")):
        return True
    if lowered.startswith(("bug:", "task:", "todo:", "ticket:", "fix:", "feature:")):
        return True
    if re.search(r"\b(?:src|tests|docs|plugins|services|project)/[\w./-]+", raw):
        return True
    return False


def _external_message_sent_text(
    *,
    state: AutoloopState,
    recent_events: list[dict[str, Any]],
) -> str:
    last_driven = _normalize_prompt_text(str(getattr(state, "last_driven_prompt", "") or ""))
    for event in reversed(recent_events):
        if str(event.get("type") or "") != "message.sent":
            continue
        text = " ".join(str(event.get("text") or "").split()).strip()
        if len(text) < 3:
            continue
        if _looks_like_autopilot_generated_prompt(text):
            continue
        if not _looks_like_explicit_intake_text(text):
            continue
        normalized = _normalize_prompt_text(text)
        if last_driven and (normalized in last_driven or last_driven.startswith(normalized)):
            continue
        return text
    return ""


def _upsert_chat_intake_operator_ticket(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    recent_events: list[dict[str, Any]],
    cycle_telemetry: dict[str, Any],
    _hp: Any,
) -> str | None:
    if not _chat_intake_ticket_enabled():
        return None
    if str(getattr(queue_result, "last_status", "") or "") != "waiting_input":
        return None
    if _waiting_ticket_has_chat_intake_label(project, queue_result):
        return None

    intake_text = _external_message_sent_text(state=state, recent_events=recent_events)
    if not intake_text:
        return None

    waiting_ticket = _llm_needs_input_waiting_ticket(queue_result)
    intake_hash = sha1(intake_text.encode("utf-8", errors="ignore")).hexdigest()[:16]
    dedupe_key = f"autopilot:chat-intake:{intake_hash}"
    title = "[OPERATOR] intake from IDE chat"
    prompt = (
        f"{title}\n\n"
        + "A new external chat message was sent in IDE while the queue "
        + "is blocked in waiting_input.\n"
        + "Create/update a dedicated operator task from this intake "
        + "instead of re-driving the old prompt.\n\n"
        + f"Origin waiting ticket: {waiting_ticket}\n"
        + f"Incoming intake:\n{intake_text}\n"
    )
    scaffold: dict[str, Any] = {
        "title": title,
        "executor_kind": "human",
        "executor_mode": "interactive",
        "labels": ["koru", "operator", "autopilot-chat-intake"],
        "source_tool": "koru-autonomous-chat-intake",
        "source_context": {
            "signal": "chat_intake_message_sent",
            "origin_waiting_ticket": waiting_ticket,
            "dedupe_key": dedupe_key,
            "intake_preview": intake_text[:200],
        },
    }
    try:
        create_task = _cycle_attr("create_nl_task", create_nl_task)
        created = create_task(
            project,
            prompt,
            queue_name="operator",
            priority="high",
            scaffold=scaffold,
        )
    except Exception as exc:
        _hp(f"- chat intake: operator ticket upsert failed ({exc})")
        return None

    cycle_telemetry["autopilot_chat_intake_ticket"] = created.ticket_id
    if getattr(created, "reused", False):
        _hp(
            "- chat intake: reused operator ticket "
            f"{created.ticket_id} (waiting={waiting_ticket})",
        )
    else:
        _hp(
            "- chat intake: created operator ticket "
            f"{created.ticket_id} (waiting={waiting_ticket})",
        )
    return created.ticket_id


def _compact_question_text(text: str, *, limit: int = 240) -> str:
    collapsed = " ".join(str(text or "").split()).strip()
    if not collapsed:
        return ""
    return collapsed[:limit]


def _extract_needs_input_question(
    reflection_events: list[Any],
    reflection_summary: str,
) -> str:
    """Best-effort extraction of the concrete question asked by IDE LLM."""
    for event in reversed(reflection_events):
        ev_type = str(getattr(event, "type", "") or "")
        if ev_type != "message.received":
            continue
        text = str(getattr(event, "text", "") or getattr(event, "summary", "") or "")
        if not text.strip():
            continue
        collapsed = _compact_question_text(text, limit=600)
        if not collapsed:
            continue
        matches = re.findall(r"([^?]{8,260}\?)", collapsed)
        if matches:
            return _compact_question_text(matches[-1], limit=240)
        for marker in (
            "please provide",
            "can you provide",
            "could you provide",
            "what is",
            "which",
            "need ",
            "missing ",
        ):
            if marker in collapsed.lower():
                return _compact_question_text(collapsed, limit=240)

    summary = _compact_question_text(reflection_summary, limit=240)
    if "?" in summary:
        return summary
    return ""


def _latest_received_text(reflection_events: list[Any]) -> str:
    for event in reversed(reflection_events):
        ev_type = str(getattr(event, "type", "") or "")
        if ev_type != "message.received":
            continue
        text = str(getattr(event, "text", "") or getattr(event, "summary", "") or "")
        if not text.strip():
            continue
        return _compact_question_text(text, limit=320)
    return ""


def _llm_needs_input_waiting_ticket(queue_result: QueueLoopResult) -> str:
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    if waiting_ticket == "-":
        waiting_ticket = str(getattr(queue_result, "last_ticket_id", "") or "-")
    return waiting_ticket


def _llm_needs_input_summary(
    queue_result: QueueLoopResult,
    reflection_summary: str,
) -> str:
    summary = (reflection_summary or "").strip()
    if summary:
        return summary
    summary = str(getattr(queue_result, "last_message", "") or "").strip()
    if summary:
        return summary
    return "IDE-side LLM requested additional input without details."


def _llm_needs_input_operator_payload(
    *,
    queue_result: QueueLoopResult,
    waiting_ticket: str,
    summary: str,
    question: str,
) -> tuple[str, str, dict[str, Any]]:
    title = f"[OPERATOR] {waiting_ticket}: provide missing IDE input"
    prompt = (
        f"{title}\n\n"
        + "IDE-side LLM asked for more context while this task is blocked in waiting_input.\n\n"
        + f"Blocked ticket: {waiting_ticket}\n"
        + f"Queue message: {str(getattr(queue_result, 'last_message', '') or '-').strip()}\n"
        + (f"Detected question: {question}\n" if question else "")
        + f"Reflection summary: {summary}\n\n"
        + "Action:\n"
        + "1. Open the related IDE chat thread.\n"
        + "2. Answer the missing question/context from this summary.\n"
        + "3. Let the LLM continue and close this operator ticket when unblocked."
    )
    scaffold: dict[str, Any] = {
        "title": title,
        "executor_kind": "human",
        "executor_mode": "interactive",
        "labels": ["koru", "operator", "autopilot-needs-input", f"waiting:{waiting_ticket}"],
        "source_tool": "koru-autonomous-llx-reflect",
        "source_context": {
            "waiting_ticket": waiting_ticket,
            "reflection_question": question,
            "reflection_summary": summary,
            "dedupe_key": f"autopilot-needs-input:{waiting_ticket}",
        },
    }
    return title, prompt, scaffold


def _note_reused_llm_needs_input_operator_ticket(
    *,
    project: Path,
    created: Any,
    waiting_ticket: str,
    question: str,
    summary: str,
    _hp: Any,
) -> None:
    try:
        from koru.queue.planfile_ticket_note import append_shell_evidence_note

        def _planfile_runner(
            command: list[str],
            cwd: Path,
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

        note = (
            "[AUTOPILOT] llx reflection still needs operator input.\n"
            + f"blocked_ticket={waiting_ticket}\n"
            + (f"question={question}\n" if question else "")
            + f"summary={summary}"
        )
        result, kind = append_shell_evidence_note(
            project,
            created.ticket_id,
            note,
            run_id=f"llx-{int(time.time())}",
            planfile_runner=_planfile_runner,
        )
        if result.returncode == 0:
            _hp(
                "- llx reflect: updated operator ticket "
                f"{created.ticket_id} ({kind})",
            )
        else:
            detail = (result.stderr or result.stdout or "").strip()
            _hp(
                "- llx reflect: operator ticket note failed "
                f"({created.ticket_id}: {detail})",
            )
    except Exception as exc:
        _hp(
            "- llx reflect: operator ticket note skipped "
            f"({created.ticket_id}: {exc})",
        )


def _upsert_llm_needs_input_operator_ticket(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    reflection_summary: str,
    reflection_events: list[Any],
    _hp: Any,
) -> str | None:
    """Create/update one deduplicated operator ticket for ``llm needs_input``."""
    if not _llm_needs_input_ticket_enabled():
        return None

    waiting_ticket = _llm_needs_input_waiting_ticket(queue_result)
    summary = _llm_needs_input_summary(queue_result, reflection_summary)
    question = _extract_needs_input_question(reflection_events, summary)

    signature_key = question or summary
    signature = f"{waiting_ticket}|{signature_key[:240]}"
    previous_signature = str(getattr(state, "last_operator_needs_input_signature", "") or "")
    previous_ticket = str(getattr(state, "last_operator_needs_input_ticket_id", "") or "")
    if signature == previous_signature:
        return previous_ticket or None

    queue_name = _llm_needs_input_ticket_queue_name()
    priority = _llm_needs_input_ticket_priority()
    _, prompt, scaffold = _llm_needs_input_operator_payload(
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        summary=summary,
        question=question,
    )

    try:
        create_task = _cycle_attr("create_nl_task", create_nl_task)
        created = create_task(
            project,
            prompt,
            queue_name=queue_name,
            priority=priority,
            scaffold=scaffold,
        )
    except Exception as exc:
        _hp(f"- llx reflect: operator ticket upsert failed ({exc})")
        return None

    state.last_operator_needs_input_signature = signature
    state.last_operator_needs_input_ticket_id = created.ticket_id

    if getattr(created, "reused", False):
        _note_reused_llm_needs_input_operator_ticket(
            project=project,
            created=created,
            waiting_ticket=waiting_ticket,
            question=question,
            summary=summary,
            _hp=_hp,
        )
    else:
        _hp(
            "- llx reflect: created operator ticket "
            f"{created.ticket_id} (queue={queue_name})",
        )
    if question:
        _hp(f"- llx reflect: operator question candidate={question!r}")
    return created.ticket_id


def _inject_reflection_summary_into_prompt(
    state: AutoloopState,
    queue_result: QueueLoopResult,
    decision: PromptDecision,
) -> PromptDecision:
    if queue_result.last_status != "waiting_input":
        return decision
    if decision.kind not in {"ticket_prompt", "fallback_prompt", "escalation_prompt"}:
        return decision
    summary = _recent_llm_reflection_summary(state)
    if not summary:
        return decision
    snippet = summary[:320]
    augmented = (
        decision.prompt.rstrip()
        + "\n\nRecent IDE chat context:\n"
        + f"- {snippet}\n"
        + "Use this context to continue from current progress. Do not restart from scratch."
    )
    return PromptDecision(
        prompt=augmented,
        kind=decision.kind,
        skip=decision.skip,
        skip_reason=decision.skip_reason,
    )


_CHAT_ACTIVITY_TYPES = ("message.sent", "message.received")


def _event_timestamp(payload: dict[str, Any], *, default: float = 0.0) -> float:
    try:
        return float(payload.get("ts") or default)
    except (TypeError, ValueError):
        return default


def _recent_chat_activity_events(
    state: AutoloopState,
    *,
    ide: str | None,
    within_seconds: float,
) -> list[dict[str, Any]]:
    now = time.time()
    recent: list[dict[str, Any]] = []
    raw_events = getattr(state, "autopilot_events", None)
    if not isinstance(raw_events, list):
        return []
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        ev_type = str(raw.get("type") or "")
        if ev_type not in _CHAT_ACTIVITY_TYPES:
            continue
        if ide and str(raw.get("ide") or "") != ide:
            continue
        ts = _event_timestamp(raw, default=0.0)
        if ts <= 0:
            continue
        if (now - ts) > within_seconds:
            continue
        recent.append(raw)
    return recent[-20:]


def _state_events_to_chat_events(recent_events: list[dict[str, Any]]) -> list[Any]:
    try:
        from koruide.chat_history import ChatEvent
    except ImportError:
        return []
    converted: list[Any] = []
    for event in recent_events:
        converted.append(
            ChatEvent(
                ts=_event_timestamp(event, default=time.time()),
                type=str(event.get("type") or ""),
                ide=str(event.get("ide") or ""),
                chat=str(event.get("chat") or "default"),
                text=str(event.get("text") or ""),
                summary=str(event.get("summary") or ""),
                length=int(event.get("length") or 0),
                reason=str(event.get("reason") or ""),
            ),
        )
    return converted


def _chat_activity_cooldown_for_state(state: AutoloopState) -> float:
    cooldown = _autopilot_redrive_cooldown_seconds()
    if cooldown <= 0:
        return cooldown
    last_kind = str(getattr(state, "last_driven_kind", "") or "")
    if last_kind == "escalation_prompt":
        return _autopilot_escalation_cooldown_seconds(cooldown)
    return cooldown


def _last_successful_drive_ack_age(
    state: AutoloopState,
    *,
    waiting_ticket: str,
    ide: str | None,
) -> float | None:
    try:
        last_sent_ts = float(getattr(state, "last_message_sent_ts", 0.0) or 0.0)
    except (TypeError, ValueError):
        last_sent_ts = 0.0
    raw_last_sent_ide = getattr(state, "last_message_sent_ide", "")
    last_sent_ide = raw_last_sent_ide if isinstance(raw_last_sent_ide, str) else ""
    if ide and last_sent_ide and last_sent_ide != ide:
        return None
    last_driven_ticket = str(getattr(state, "last_driven_ticket_id", "") or "")
    if waiting_ticket == "-" or last_driven_ticket != waiting_ticket or last_sent_ts <= 0:
        return None
    return max(0.0, time.time() - last_sent_ts)


def _event_matches_last_driven_prompt(
    state: AutoloopState,
    event: dict[str, Any],
) -> bool:
    if str(event.get("type") or "") != "message.sent":
        return False
    event_text = _normalize_prompt_text(str(event.get("text") or ""))
    last_driven = _normalize_prompt_text(str(getattr(state, "last_driven_prompt", "") or ""))
    if not event_text or not last_driven:
        return False
    return event_text == last_driven or event_text in last_driven or last_driven in event_text


def _last_self_drive_event_age(
    state: AutoloopState,
    recent_events: list[dict[str, Any]],
) -> float | None:
    for event in reversed(recent_events):
        if not _event_matches_last_driven_prompt(state, event):
            continue
        return max(0.0, time.time() - _event_timestamp(event, default=0.0))
    return None


def _llx_chat_reflection_enabled() -> bool:
    try:
        from koru.llm_reflect import llm_reflect_enabled
    except ImportError:
        return False
    return bool(llm_reflect_enabled())


def _recent_message_sent_allows_redrive(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    recent_events: list[dict[str, Any]],
    last_type: str,
    age: str,
    waiting_ticket: str,
    _hp: Any,
) -> bool:
    from koru.autonomous_cycle_skip_conditions import _waiting_ticket_has_label

    has_received = any(str(ev.get("type") or "") == "message.received" for ev in recent_events)
    last_kind = str(getattr(state, "last_driven_kind", "") or "")
    if not (
        last_type == "message.sent"
        and not has_received
        and getattr(queue_result, "last_status", "") == "waiting_input"
        and last_kind != "escalation_prompt"
        and not _waiting_ticket_has_label(project, queue_result, "llm-ready")
    ):
        return False
    _hp(
        "- autopilot redrive allowed (message.sent without "
        f"message.received age={age} ticket={waiting_ticket})",
    )
    return True


def _recent_chat_history_fallback(
    *,
    ide: str | None,
    cooldown: float,
    reflection_events: list[Any],
) -> tuple[str, str, list[Any]] | None:
    try:
        from koruide.chat_history import has_recent_activity, last_event, read_events
    except ImportError:
        return None
    if not has_recent_activity(
        ide=ide,
        within_seconds=cooldown,
        types=_CHAT_ACTIVITY_TYPES,
    ):
        return None
    last = last_event(ide=ide, types=_CHAT_ACTIVITY_TYPES)
    age = f"{last.age_seconds:.0f}s" if last is not None else "?"
    last_type = last.type if last is not None else "?"
    if not reflection_events:
        reflection_events = read_events(
            ide=ide,
            max_age_seconds=cooldown,
            types=_CHAT_ACTIVITY_TYPES,
            limit=20,
        )
    return last_type, age, reflection_events


def _upsert_reflection_needs_input_ticket(
    *,
    reflection: Any,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    summary: str,
    reflection_events: list[Any],
    cycle_telemetry: dict[str, Any],
    _hp: Any,
) -> None:
    """Upsert an operator ticket when reflection indicates needs_input and not done."""
    if not (reflection.needs_input and not reflection.done):
        return
    operator_ticket = _upsert_llm_needs_input_operator_ticket(
        project=project,
        queue_result=queue_result,
        state=state,
        reflection_summary=summary,
        reflection_events=reflection_events,
        _hp=_hp,
    )
    if operator_ticket:
        cycle_telemetry["autopilot_llx_operator_ticket"] = operator_ticket


def _apply_llx_chat_reflection(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    waiting_ticket: str,
    ide: str | None,
    reflection_events: list[Any],
    _hp: Any,
) -> tuple[bool, bool]:
    try:
        from koru.llm_reflect import llm_reflect_enabled, reflect_on_chat
    except ImportError:
        return False, False
    if not llm_reflect_enabled():
        return False, False
    ticket_title = getattr(queue_result, "last_message", "") or ""
    raw_driven_prompt = getattr(state, "last_driven_prompt", "")
    driven_prompt = raw_driven_prompt if isinstance(raw_driven_prompt, str) else ""
    reflection = reflect_on_chat(
        ticket_id=waiting_ticket or "-",
        ticket_title=ticket_title,
        driven_prompt=driven_prompt or ticket_title,
        ide=ide or "",
        events=reflection_events or None,
    )
    if reflection is None:
        return False, False
    cycle_telemetry["autopilot_llx_reflection"] = {
        "done": reflection.done,
        "needs_input": reflection.needs_input,
        "summary": reflection.summary,
    }
    summary = (reflection.summary or "").strip()
    if summary:
        state.last_llm_reflection_summary = summary[:320]
        state.last_llm_reflection_ts = time.time()
    _hp(
        "- llx reflect: "
        f"done={reflection.done} needs_input={reflection.needs_input} "
        f"summary={reflection.summary!r}",
    )
    _upsert_reflection_needs_input_ticket(
        reflection=reflection,
        project=project,
        queue_result=queue_result,
        state=state,
        summary=summary,
        reflection_events=reflection_events,
        cycle_telemetry=cycle_telemetry,
        _hp=_hp,
    )
    return True, bool(reflection.done)


def _apply_needs_input_heuristic(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    reflection_events: list[Any],
    _hp: Any,
) -> None:
    if not _llm_needs_input_heuristic_enabled():
        return
    question = _extract_needs_input_question(reflection_events, "")
    if not question:
        return
    operator_ticket = _upsert_llm_needs_input_operator_ticket(
        project=project,
        queue_result=queue_result,
        state=state,
        reflection_summary=_latest_received_text(reflection_events) or question,
        reflection_events=reflection_events,
        _hp=_hp,
    )
    if operator_ticket:
        cycle_telemetry["autopilot_needs_input_heuristic"] = True
        cycle_telemetry["autopilot_llx_operator_ticket"] = operator_ticket
    _hp(f"- needs_input heuristic: question={question!r}")


def _check_recent_drive_ack_skip(
    state: AutoloopState,
    cooldown: float,
    waiting_ticket: str,
    ide: str | None,
    cycle_telemetry: dict[str, Any],
    _hp: Any,
) -> bool:
    drive_ack_age = _last_successful_drive_ack_age(
        state,
        waiting_ticket=waiting_ticket,
        ide=ide,
    )
    if drive_ack_age is not None and drive_ack_age <= cooldown:
        age = f"{drive_ack_age:.0f}s"
        cycle_telemetry["autopilot_skipped_chat_activity"] = True
        cycle_telemetry["autopilot_chat_activity_last_event"] = "drive.ack"
        _hp(
            "- autopilot skipped (recent_drive_ack "
            f"last=drive.ack age={age} cooldown={cooldown:.0f}s "
            f"ticket={waiting_ticket})",
        )
        return True
    return False


def _check_chat_intake_skip(
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    recent_events: list[dict[str, Any]],
    cycle_telemetry: dict[str, Any],
    _hp: Any,
) -> bool:
    intake_ticket = _upsert_chat_intake_operator_ticket(
        project=project,
        queue_result=queue_result,
        state=state,
        recent_events=recent_events,
        cycle_telemetry=cycle_telemetry,
        _hp=_hp,
    )
    if intake_ticket:
        cycle_telemetry["autopilot_skipped_chat_intake"] = True
        return True
    return False


def _check_recent_self_drive_skip(
    state: AutoloopState,
    cooldown: float,
    waiting_ticket: str,
    recent_events: list[dict[str, Any]],
    cycle_telemetry: dict[str, Any],
    _hp: Any,
) -> bool:
    has_received = any(str(ev.get("type") or "") == "message.received" for ev in recent_events)
    self_drive_age = _last_self_drive_event_age(state, recent_events)
    if (
        self_drive_age is not None
        and self_drive_age <= cooldown
        and not has_received
        and not _llx_chat_reflection_enabled()
    ):
        age = f"{self_drive_age:.0f}s"
        cycle_telemetry["autopilot_skipped_chat_activity"] = True
        cycle_telemetry["autopilot_chat_activity_last_event"] = "message.sent"
        _hp(
            "- autopilot skipped (recent_self_drive "
            f"last=message.sent age={age} cooldown={cooldown:.0f}s "
            f"ticket={waiting_ticket})",
        )
        return True
    return False


def _determine_chat_activity_status(
    state: AutoloopState,
    queue_result: QueueLoopResult,
    project: Path,
    cooldown: float,
    waiting_ticket: str,
    ide: str | None,
    recent_events: list[dict[str, Any]],
    reflection_events: list[Any],
    _hp: Any,
) -> tuple[bool, str, str, list[Any]]:
    if recent_events:
        last_payload = recent_events[-1]
        last_type = str(last_payload.get("type") or "?")
        age_seconds = max(0.0, time.time() - _event_timestamp(last_payload, default=0.0))
        age = f"{age_seconds:.0f}s"
        if _recent_message_sent_allows_redrive(
            project=project,
            queue_result=queue_result,
            state=state,
            recent_events=recent_events,
            last_type=last_type,
            age=age,
            waiting_ticket=waiting_ticket,
            _hp=_hp,
        ):
            return False, "", "", []
        return True, last_type, age, reflection_events
    else:
        fallback = _recent_chat_history_fallback(
            ide=ide,
            cooldown=cooldown,
            reflection_events=reflection_events,
        )
        if fallback is None:
            return False, "", "", []
        last_type, age, reflection_events = fallback
        return True, last_type, age, reflection_events


def _skip_due_to_recent_chat_activity(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    _hp: Any,
) -> bool:
    """Return True iff the loop should skip drive because the IDE chat is busy.

    Two signals (both optional, fail-closed → no skip):

    1. Plain cooldown: ``message.sent`` for the same ticket within
       :func:`_autopilot_redrive_cooldown_seconds`. This is the cheap path —
       no llx, no network — and covers the common case where koru just drove
       the prompt and the LLM is still streaming a response.
    2. Optional :mod:`koru.llm_reflect` (when enabled and llx
       is on PATH). Asks an OpenRouter-backed model to read the recent
       ``message.received`` events and decide ``{done, needs_input}``. If
         it returns ``needs_input=true`` we skip and upsert one operator ticket;
         if ``done=true`` we also skip redrive and let the queue state update
         naturally.
    """
    cooldown = _chat_activity_cooldown_for_state(state)
    if cooldown <= 0:
        return False

    ide = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip().lower() or None
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)

    if _check_recent_drive_ack_skip(state, cooldown, waiting_ticket, ide, cycle_telemetry, _hp):
        return True

    recent_events = _recent_chat_activity_events(
        state,
        ide=ide,
        within_seconds=cooldown,
    )
    reflection_events = _state_events_to_chat_events(recent_events)

    if _check_chat_intake_skip(project, queue_result, state, recent_events, cycle_telemetry, _hp):
        return True

    if _check_recent_self_drive_skip(
        state,
        cooldown,
        waiting_ticket,
        recent_events,
        cycle_telemetry,
        _hp,
    ):
        return True

    has_activity, last_type, age, reflection_events = _determine_chat_activity_status(
        state=state,
        queue_result=queue_result,
        project=project,
        cooldown=cooldown,
        waiting_ticket=waiting_ticket,
        ide=ide,
        recent_events=recent_events,
        reflection_events=reflection_events,
        _hp=_hp,
    )
    if not has_activity:
        return False

    cycle_telemetry["autopilot_skipped_chat_activity"] = True
    cycle_telemetry["autopilot_chat_activity_last_event"] = last_type
    _hp(
        "- autopilot skipped (recent_chat_activity "
        f"last={last_type} age={age} cooldown={cooldown:.0f}s "
        f"ticket={waiting_ticket})",
    )
    reflection_resolved, reflection_done = _apply_llx_chat_reflection(
        project=project,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=cycle_telemetry,
        waiting_ticket=waiting_ticket,
        ide=ide,
        reflection_events=reflection_events,
        _hp=_hp,
    )
    if reflection_done:
        return True

    # Fallback for environments where llx/OpenRouter is unavailable.
    if not reflection_resolved:
        _apply_needs_input_heuristic(
            project=project,
            queue_result=queue_result,
            state=state,
            cycle_telemetry=cycle_telemetry,
            reflection_events=reflection_events,
            _hp=_hp,
        )
    return True
