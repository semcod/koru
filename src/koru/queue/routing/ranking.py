"""Candidate ranking and routing decisions based on capabilities and daily probe evidence."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from .contracts import Candidate, Decision, ProbeResult, Task, ToolClass


def rank_candidates(
    task: Task,
    candidates: Sequence[Candidate],
    evidence: Mapping[str, ProbeResult] | None = None,
    explicit_choice: str | None = None,
    evidence_date: str | None = None,
) -> Decision:
    """Select the best candidate for a task.

    Explicit selection always wins (AC-01). Otherwise, filters by availability
    and capability, then ranks by validated probe outcomes, speed and cost.
    """
    evidence = evidence or {}
    rejected: dict[str, str] = {}

    # AC-01: Explicit selection wins
    if explicit_choice:
        choice_clean = explicit_choice.strip().lower()
        for cand in candidates:
            cand_full = f"{cand.client}/{cand.model}".lower() if cand.model else cand.client.lower()
            if (
                cand.id.lower() == choice_clean
                or cand.client.lower() == choice_clean
                or (cand.model and cand.model.lower() == choice_clean)
                or cand_full == choice_clean
            ):
                probe = evidence.get(f"{cand.id}:{task.key}") or evidence.get(cand.id)
                samples = 1 if probe else 0
                return Decision(
                    candidate=cand,
                    task=task,
                    reason=f"explicit_selection({explicit_choice})",
                    evidence_date=evidence_date,
                    samples=samples,
                    low_confidence=False,
                    rejected={},
                )

    # Filter by availability and capability
    eligible: list[Candidate] = []
    for cand in candidates:
        if not cand.available:
            rejected[cand.id] = f"unavailable: {cand.unavailable_reason or 'offline'}"
            continue
        if not cand.supports(task):
            rejected[cand.id] = f"unsupported_capability: requires {task.key}"
            continue
        eligible.append(cand)

    if not eligible:
        return Decision(
            candidate=None,
            task=task,
            reason="no_supported_candidate",
            evidence_date=evidence_date,
            samples=0,
            low_confidence=True,
            rejected=rejected,
        )

    def _sort_key(c: Candidate) -> tuple[int, int, float, int]:
        probe = evidence.get(f"{c.id}:{task.key}") or evidence.get(c.id)
        # Tier 0: verified probe pass
        # Tier 1: unprobed candidate
        # Tier 2: failed probe
        if probe and probe.status in {"ok", "verified", "passed"}:
            tier = 0
            duration = probe.duration_ms
            cost = probe.cost if probe.cost is not None else 0.0
        elif probe and probe.status in {"failed", "error", "timeout"}:
            tier = 2
            duration = probe.duration_ms
            cost = probe.cost if probe.cost is not None else 999.0
        else:
            tier = 1
            duration = 1000
            cost = 0.0

        # Preference: deterministic for simple tasks, cli/api for complex
        tool_preference = 0
        if task.difficulty == "simple" and c.tool_class == ToolClass.DETERMINISTIC:
            tool_preference = -1

        return (tier, tool_preference, duration, cost)

    eligible.sort(key=_sort_key)
    chosen = eligible[0]

    chosen_probe = evidence.get(f"{chosen.id}:{task.key}") or evidence.get(chosen.id)
    if chosen_probe and chosen_probe.status in {"ok", "verified", "passed"}:
        reason = f"verified_probe(status={chosen_probe.status}, duration={chosen_probe.duration_ms}ms)"
        low_confidence = False
        samples = 1
    else:
        reason = f"default_capability({chosen.id})"
        low_confidence = True
        samples = 0

    return Decision(
        candidate=chosen,
        task=task,
        reason=reason,
        evidence_date=evidence_date,
        samples=samples,
        low_confidence=low_confidence,
        rejected=rejected,
    )
