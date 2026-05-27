"""LLM-needs-input operator ticket subsystem.

Extracted from :mod:`koru.autonomous_cycle_chat_activity` (R7a — FAZA 2)
to isolate the deduplicated operator-ticket upsert pipeline used when the
IDE-side LLM signals ``needs_input``. The original module re-exports all
symbols so legacy imports keep working.
"""

from __future__ import annotations

import subprocess
import time
from hashlib import sha1
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_chat_activity_config import (
    chat_intake_ticket_enabled as _chat_intake_ticket_enabled,
    llm_needs_input_ticket_enabled as _llm_needs_input_ticket_enabled,
    llm_needs_input_ticket_priority as _llm_needs_input_ticket_priority,
    llm_needs_input_ticket_queue_name as _llm_needs_input_ticket_queue_name,
    llm_reflection_summary_max_age_seconds as _llm_reflection_summary_max_age_seconds,
)
from koru.autonomous_cycle_chat_activity_text import (
    extract_needs_input_question as _extract_needs_input_question,
    looks_like_autopilot_generated_prompt as _looks_like_autopilot_generated_prompt,
    looks_like_explicit_intake_text as _looks_like_explicit_intake_text,
    normalize_prompt_text as _normalize_prompt_text,
)
from koru.autonomous_cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.tasks import create_nl_task


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


def _waiting_ticket_has_chat_intake_label(
    project: Path,
    queue_result: QueueLoopResult,
) -> bool:
    try:
        from koru.autonomous_cycle_skip_conditions import _waiting_ticket_has_label
    except ImportError:
        return False
    return _waiting_ticket_has_label(project, queue_result, "autopilot-chat-intake")


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
    report_progress: Any,
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
        from koru import autonomous_cycle as _cycle_mod

        create_task = getattr(_cycle_mod, "create_nl_task", create_nl_task)
        created = create_task(
            project,
            prompt,
            queue_name="operator",
            priority="high",
            scaffold=scaffold,
        )
    except Exception as exc:
        report_progress(f"- chat intake: operator ticket upsert failed ({exc})")
        return None

    cycle_telemetry["autopilot_chat_intake_ticket"] = created.ticket_id
    if getattr(created, "reused", False):
        report_progress(
            "- chat intake: reused operator ticket "
            f"{created.ticket_id} (waiting={waiting_ticket})",
        )
    else:
        report_progress(
            "- chat intake: created operator ticket "
            f"{created.ticket_id} (waiting={waiting_ticket})",
        )
    return created.ticket_id


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
    report_progress: Any,
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
            report_progress(
                "- llx reflect: updated operator ticket "
                f"{created.ticket_id} ({kind})",
            )
        else:
            detail = (result.stderr or result.stdout or "").strip()
            report_progress(
                "- llx reflect: operator ticket note failed "
                f"({created.ticket_id}: {detail})",
            )
    except Exception as exc:
        report_progress(
            "- llx reflect: operator ticket note skipped "
            f"({created.ticket_id}: {exc})",
        )


def _llm_needs_input_signature(waiting_ticket: str, question: str, summary: str) -> str:
    signature_key = question or summary
    return f"{waiting_ticket}|{signature_key[:240]}"


def _previous_llm_needs_input_ticket(
    state: AutoloopState,
    signature: str,
) -> str | None:
    previous_signature = str(getattr(state, "last_operator_needs_input_signature", "") or "")
    if signature != previous_signature:
        return None
    previous_ticket = str(getattr(state, "last_operator_needs_input_ticket_id", "") or "")
    return previous_ticket or None


def _create_llm_needs_input_operator_task(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    waiting_ticket: str,
    summary: str,
    question: str,
    queue_name: str,
    priority: str,
    report_progress: Any,
) -> Any | None:
    operator_payload = _llm_needs_input_operator_payload(
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        summary=summary,
        question=question,
    )
    try:
        # Resolve ``create_nl_task`` via ``koru.autonomous_cycle`` so existing
        # tests that monkeypatch ``koru.autonomous_cycle.create_nl_task`` keep
        # affecting this code path after the R7a extraction.
        from koru import autonomous_cycle as _cycle_mod

        create_task = getattr(_cycle_mod, "create_nl_task", create_nl_task)
        return create_task(
            project,
            operator_payload[1],
            queue_name=queue_name,
            priority=priority,
            scaffold=operator_payload[2],
        )
    except Exception as exc:
        report_progress(f"- llx reflect: operator ticket upsert failed ({exc})")
        return None


def _remember_llm_needs_input_operator_ticket(
    state: AutoloopState,
    signature: str,
    ticket_id: str,
) -> None:
    state.last_operator_needs_input_signature = signature
    state.last_operator_needs_input_ticket_id = ticket_id


def _report_llm_needs_input_operator_ticket(
    *,
    project: Path,
    created: Any,
    waiting_ticket: str,
    question: str,
    summary: str,
    queue_name: str,
    report_progress: Any,
) -> None:
    if getattr(created, "reused", False):
        _note_reused_llm_needs_input_operator_ticket(
            project=project,
            created=created,
            waiting_ticket=waiting_ticket,
            question=question,
            summary=summary,
            report_progress=report_progress,
        )
    else:
        report_progress(
            "- llx reflect: created operator ticket "
            f"{created.ticket_id} (queue={queue_name})",
        )
    if question:
        report_progress(f"- llx reflect: operator question candidate={question!r}")


def _upsert_llm_needs_input_operator_ticket(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    reflection_summary: str,
    reflection_events: list[Any],
    report_progress: Any,
) -> str | None:
    """Create/update one deduplicated operator ticket for ``llm needs_input``."""
    if not _llm_needs_input_ticket_enabled():
        return None

    waiting_ticket = _llm_needs_input_waiting_ticket(queue_result)
    summary = _llm_needs_input_summary(queue_result, reflection_summary)
    question = _extract_needs_input_question(reflection_events, summary)
    signature = _llm_needs_input_signature(waiting_ticket, question, summary)
    previous_ticket = _previous_llm_needs_input_ticket(state, signature)
    if previous_ticket is not None:
        return previous_ticket

    queue_name = _llm_needs_input_ticket_queue_name()
    priority = _llm_needs_input_ticket_priority()
    created = _create_llm_needs_input_operator_task(
        project=project,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        summary=summary,
        question=question,
        queue_name=queue_name,
        priority=priority,
        report_progress=report_progress,
    )
    if created is None:
        return None

    _remember_llm_needs_input_operator_ticket(state, signature, created.ticket_id)
    _report_llm_needs_input_operator_ticket(
        project=project,
        created=created,
        waiting_ticket=waiting_ticket,
        question=question,
        summary=summary,
        queue_name=queue_name,
        report_progress=report_progress,
    )
    return created.ticket_id
