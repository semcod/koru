from __future__ import annotations

import json
from typing import Any

from koru.autonomy.verification_engine import Evidence, Verdict


def build_evaluate_drive_result_prompt(
    evidence: Evidence,
    *,
    ticket_id: str = "",
    ticket_title: str = "",
    driven_prompt: str = "",
    heuristic_verdict: Verdict | None = None,
) -> str:
    prompt_parts = [
        "Evaluate whether an IDE autopilot drive accomplished the task.",
        "",
        f"Ticket: {ticket_id or '(none)'}",
        f"Title: {ticket_title or '(none)'}",
        f"Driven prompt: {driven_prompt[:500]}" if driven_prompt else "",
        "",
        "Evidence collected after drive:",
        f"  Git files changed: {evidence.git.files_changed}",
        f"  Git insertions: {evidence.git.insertions}",
        f"  Git deletions: {evidence.git.deletions}",
        f"  Test status: {evidence.tests.status}",
        f"  Failing services: {', '.join(evidence.tests.failing_services) or 'none'}",
        f"  Chat events since drive: {evidence.chat.events_since_drive}",
        f"  Chat has message.sent: {evidence.chat.has_message_sent}",
        f"  Chat session ended: {evidence.chat.has_session_ended}",
    ]
    if heuristic_verdict:
        prompt_parts.extend([
            "",
            "Heuristic verdict (for reference):",
            f"  Outcome: {heuristic_verdict.outcome}",
            f"  Confidence: {heuristic_verdict.confidence}",
            f"  Reason: {heuristic_verdict.reason}",
        ])
    prompt_parts.extend([
        "",
        'Return JSON: {"outcome":"completed|in_progress|no_change|degraded",'
        '"confidence":0.0-1.0,"reason":"short explanation",'
        '"suggestion":"what to do next"}',
    ])
    return "\n".join(p for p in prompt_parts if p is not None)


def build_generate_better_prompt_prompt(
    *,
    ticket_id: str,
    ticket_title: str,
    original_prompt: str,
    drive_count: int,
    last_verdict_reason: str = "",
    evidence_summary: str = "",
) -> str:
    return "\n".join([
        "The following autopilot prompt has been driven to an IDE LLM multiple times "
        "but the task remains incomplete.",
        "",
        f"Ticket: {ticket_id}",
        f"Title: {ticket_title}",
        f"Drive attempts: {drive_count}",
        f"Last verdict: {last_verdict_reason}" if last_verdict_reason else "",
        f"Evidence: {evidence_summary[:300]}" if evidence_summary else "",
        "",
        "Original prompt:",
        original_prompt[:2000],
        "",
        "Generate an improved version of this prompt that:",
        "1. Is more specific about what needs to change",
        "2. Mentions files or functions if evident from the context",
        "3. Avoids repeating instructions the LLM already tried",
        "4. Stays concise (under 500 words)",
        "",
        'Return JSON: {"improved_prompt":"the new prompt text","changes":"what you changed and why"}',
    ])


def build_plan_next_action_prompt(
    *,
    queue_status: str,
    waiting_tickets: list[str],
    stagnation_streak: int,
    test_status: str,
    last_verdict: dict[str, Any] | None = None,
    last_action_plan: dict[str, Any] | None = None,
) -> str:
    prompt_parts = [
        "You are the planning brain of an autonomous coding assistant (koru).",
        "Given the current project state, recommend the next action.",
        "",
        f"Queue status: {queue_status}",
        f"Waiting tickets: {', '.join(waiting_tickets) or 'none'}",
        f"Stagnation streak: {stagnation_streak}",
        f"Test status: {test_status}",
    ]
    if last_verdict:
        prompt_parts.append(f"Last drive verdict: {json.dumps(last_verdict)[:500]}")
    if last_action_plan:
        prompt_parts.append(f"Last action plan: {json.dumps(last_action_plan)[:500]}")
    prompt_parts.extend([
        "",
        "Possible actions: drive_ticket, redrive_improved, close_ticket, "
        "escalate_ticket, switch_ticket, run_discovery, wait, reflect, noop",
        "",
        'Return JSON: {"action":"one_of_above","ticket_id":"or null",'
        '"reason":"short","confidence":0.0-1.0}',
    ])
    return "\n".join(prompt_parts)


def build_reflect_on_chat_prompt(
    *,
    ticket_id: str,
    ticket_title: str,
    driven_prompt: str,
    chat_events: list[dict[str, Any]],
) -> str:
    event_lines = []
    for ev in chat_events[-20:]:
        etype = str(ev.get("type", ""))
        text = str(ev.get("text", "") or ev.get("summary", ""))[:200]
        event_lines.append(f"  [{etype}] {text}")

    return "\n".join([
        "You are a reflection assistant for the koru autonomous loop.",
        "The loop just drove the prompt below into the IDE chat.",
        "Based ONLY on the recent IDE chat events, decide:",
        "  - done = true: IDE produced a final answer or completed the task",
        "  - needs_input = true: IDE is asking a question and is blocked",
        "  - otherwise (still working): both false",
        "",
        f"Ticket: {ticket_id or '-'} — {ticket_title or '-'}",
        f"Driven prompt: {driven_prompt[:500]}",
        "",
        "Recent IDE chat events (newest last):",
        *event_lines,
        "",
        'Return JSON: {"done":bool,"needs_input":bool,"summary":"1 sentence"}',
    ])


def build_propose_strategy_tuning_prompt(
    *,
    current_strategy_yaml: str,
    recent_decisions: list[dict[str, Any]],
    cycle_metrics: dict[str, Any] | None = None,
) -> str:
    decisions_summary = json.dumps(recent_decisions[-10:], indent=1)[:2000]
    prompt_parts = [
        "You are helping tune Koru autonomy strategy based on telemetry.",
        "",
        "Current autonomy.strategy (koru.yaml):",
        "```yaml",
        current_strategy_yaml[:1500],
        "```",
        "",
        f"Recent decision history ({len(recent_decisions)} decisions, last 10 shown):",
        "```json",
        decisions_summary,
        "```",
    ]
    if cycle_metrics:
        prompt_parts.extend([
            "",
            f"Latest cycle metrics: {json.dumps(cycle_metrics)[:500]}",
        ])
    prompt_parts.extend([
        "",
        "Analyze patterns:",
        "- Are there too many stagnation/escalation events?",
        "- Should cooldown or idle_streak thresholds change?",
        "- Is the pipeline order optimal?",
        "- Any signals being ignored that should be added?",
        "",
        'Return JSON: {"patch":"yaml or diff","reason":"explanation","confidence":0.0-1.0}',
        'Set patch to empty string if no changes recommended.',
    ])
    return "\n".join(prompt_parts)


def build_prioritize_tickets_prompt(
    *,
    tickets: list[dict[str, Any]],
    test_status: str = "unknown",
    recent_verdicts: list[dict[str, Any]] | None = None,
) -> str:
    ticket_lines = []
    for t in tickets[:20]:
        tid = str(t.get("id", "?"))
        title = str(t.get("title", ""))[:100]
        status = str(t.get("status", ""))
        ticket_lines.append(f"  {tid}: {title} [{status}]")

    prompt_parts = [
        "You are prioritizing work tickets for an autonomous coding assistant.",
        "",
        f"Test status: {test_status}",
        "",
        "Available tickets:",
        *ticket_lines,
    ]
    if recent_verdicts:
        prompt_parts.extend([
            "",
            f"Recent drive verdicts: {json.dumps(recent_verdicts[-5:])[:500]}",
        ])
    prompt_parts.extend([
        "",
        "Order tickets by execution priority. Consider:",
        "- Tickets related to failing tests should come first",
        "- Small, focused tickets before large refactors",
        "- Tickets with recent failed drives might need different approach",
        "",
        'Return JSON: {"ordered":["ticket-id-1","ticket-id-2",...],'
        '"reason":"short explanation","confidence":0.0-1.0}',
    ])
    return "\n".join(prompt_parts)
