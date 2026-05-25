"""LLM-needs-input operator ticket subsystem.

Extracted from :mod:`koru.autonomous_cycle_chat_activity` (R7a — FAZA 2)
to isolate the deduplicated operator-ticket upsert pipeline used when the
IDE-side LLM signals ``needs_input``. The original module re-exports all
symbols so legacy imports keep working.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_chat_activity_config import (
    llm_needs_input_ticket_enabled as _llm_needs_input_ticket_enabled,
    llm_needs_input_ticket_priority as _llm_needs_input_ticket_priority,
    llm_needs_input_ticket_queue_name as _llm_needs_input_ticket_queue_name,
)
from koru.autonomous_cycle_chat_activity_text import (
    extract_needs_input_question as _extract_needs_input_question,
)
from koru.autonomous_cycle_common import _queue_loop_waiting_ticket_label
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.tasks import create_nl_task


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
        # Resolve ``create_nl_task`` via ``koru.autonomous_cycle`` so existing
        # tests that monkeypatch ``koru.autonomous_cycle.create_nl_task`` keep
        # affecting this code path after the R7a extraction.
        from koru import autonomous_cycle as _cycle_mod

        create_task = getattr(_cycle_mod, "create_nl_task", create_nl_task)
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
