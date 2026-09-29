"""Heuristic verdict assessment (pure, no LLM)."""

from koru.autonomy.verification_engine.models import Evidence, Verdict, VerdictOutcome


def assess_verdict(
    evidence: Evidence,
    *,
    ticket_id: str = "",
    drive_count: int = 1,
) -> Verdict:
    """Produce a heuristic verdict from collected evidence.

    Scoring:
      - git changes present               → +0.4
      - tests passing                      → +0.3
      - chat activity (message.sent)       → +0.2
      - session ended (IDE done working)   → +0.1
    """
    score = 0.0
    reasons: list[str] = []

    # Git evidence
    if evidence.git.files_changed > 0:
        score += 0.4
        reasons.append(f"git: {evidence.git.files_changed} files changed")
    else:
        reasons.append("git: no changes")

    # Test evidence
    if evidence.tests.status == "ok":
        score += 0.3
        reasons.append("tests: passing")
    elif evidence.tests.status in {"changed", "unknown"}:
        score += 0.1
        reasons.append(f"tests: {evidence.tests.status}")
    elif evidence.tests.status in {"failing", "failed", "error", "down"}:
        score -= 0.2
        reasons.append(f"tests: {evidence.tests.status}")

    # Chat evidence
    if evidence.chat.has_message_sent:
        score += 0.2
        reasons.append("chat: message.sent detected")
    if evidence.chat.has_session_ended:
        score += 0.1
        reasons.append("chat: session.ended")

    # Clamp to [0, 1]
    score = max(0.0, min(1.0, score))

    # Determine outcome
    if evidence.tests.status in {"failing", "failed", "error", "down"}:
        outcome: VerdictOutcome = "degraded"
    elif not evidence.git.observed:
        outcome = "unknown"
        reasons.append("git: observation unavailable")
    elif evidence.verification_passed:
        outcome = "completed"
        score = 1.0
        reasons.append("verification: matching drive passed")
    elif score >= 0.3:
        outcome = "in_progress"
    elif evidence.git.files_changed == 0 and not evidence.chat.has_message_sent:
        outcome = "no_change"
    else:
        outcome = "unknown"

    # Penalise repeated failures
    if drive_count > 2 and outcome == "no_change":
        reasons.append(f"stagnant after {drive_count} drives")

    return Verdict(
        outcome=outcome,
        confidence=round(score, 2),
        reason="; ".join(reasons),
        evidence=evidence,
        ticket_id=ticket_id,
    )


# ---------------------------------------------------------------------------
# Helpers
