"""Retry policy for patch tickets, and the evidence a finished run leaves.

Sits above the deterministic transaction: it decides *whether to ask the agent
again*, which is a policy question, while the transaction only decides whether
a given patch may land. Only mechanical failures — a malformed diff, one that
no longer applies — are retried, because those are the ones a model can fix
once it sees the diagnostic. A patch that applied but failed its gate is wrong
on the merits, and re-asking would spend another agent run on the same idea.

Because this layer owns the whole run — every attempt, the pinned base, the
final outcome — it is also where the evidence bundle is assembled and written.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple
from uuid import uuid4

from koru.queue.evidence import (
    VERDICT_APPLIED,
    VERDICT_ARTIFACT,
    VERDICT_REFUSED,
    VERDICT_VERIFIED,
    build_evidence_bundle,
    patch_attempt_record,
    persist_evidence,
    provenance_from_result,
)
from koru.queue.journal import PHASE_COMPLETED, RunJournal
from koru.queue.patch_mode import (
    MANIFEST_MISMATCH,
    NO_PATCH_EMITTED,
    PATCH_DOES_NOT_APPLY,
    PROMOTION_ARTIFACT,
    PROMOTION_BRANCH,
    VERIFY_BASELINE_FAILED,
    VERIFY_FAILED_ISOLATED,
    VERIFY_FAILED_ROLLED_BACK,
    PatchOutcome,
    build_manifest,
    build_retry_prompt,
    build_verify_retry_prompt,
    current_file_excerpt,
    diff_target_files,
    extract_unified_diff,
    manifest_drift,
    persist_manifest,
    promotion_mode,
    redact_secrets,
    wrap_reply_in_proposal_envelope,
)
from koru.queue.transaction.result import PatchPlan, PatchTransactionResult
from koru.queue.types import CommandResult
from koru.queue.workspace import branch_head


def patch_retry_budget(ticket: dict | None = None) -> int:
    """How many times to re-ask an agent whose diff would not apply."""
    if ticket is not None:
        per_ticket = (ticket.get("inputs") or {}).get("max_patch_attempts")
        if per_ticket is not None:
            try:
                return max(0, int(per_ticket))
            except (TypeError, ValueError):
                pass
        execution = ticket.get("execution") or {}
        exec_attempts = execution.get("max_attempts")
        if exec_attempts is not None:
            try:
                return max(0, int(exec_attempts))
            except (TypeError, ValueError):
                pass
    raw = (os.environ.get("KORU_QUEUE_PATCH_RETRIES") or "").strip()
    try:
        return max(0, int(raw)) if raw else 1
    except ValueError:
        return 1


def verify_retry_budget(ticket: dict | None = None) -> int:
    """How many times to re-ask an agent when a patch applied cleanly but failed verification."""
    if ticket is not None:
        per_ticket = (ticket.get("inputs") or {}).get("max_verify_retries")
        if per_ticket is not None:
            try:
                return max(0, int(per_ticket))
            except (TypeError, ValueError):
                pass
    raw = (os.environ.get("KORU_QUEUE_VERIFY_RETRIES") or "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            return 0
    if isinstance(ticket, dict):
        declared = _filter_readonly_scan_artifacts(ticket.get("files") or ())
        if len(declared) > 1:
            return 1
    return 0


_UNRECOVERABLE_BASELINE_MARKERS = (
    "no tests ran",
    "ModuleNotFoundError",
    "No module named ",
    "command not found",
    "verification_sandbox_unavailable",
)


def _is_verify_failure(outcome: PatchOutcome | None) -> bool:
    if outcome is None or not outcome.workspace_left_untouched:
        return False
    if outcome.code in (VERIFY_FAILED_ISOLATED, VERIFY_FAILED_ROLLED_BACK):
        return True
    if outcome.code == VERIFY_BASELINE_FAILED:
        msg = outcome.message or ""
        if any(marker in msg for marker in _UNRECOVERABLE_BASELINE_MARKERS):
            return False
        if " Before: " in msg and " After: " in msg:
            before_part, after_part = msg.rsplit(" Before: ", 1)[1].split(" After: ", 1)
            if before_part.strip() == after_part.strip():
                return False
        return True
    return False


def _contract_capped_budget(project: Path, ticket: dict) -> int:
    """The retry budget, never above what the ticket's contract permits.

    The contract caps *attempts*; the budget counts *retries*, so a contract
    max_attempts of 2 leaves room for one re-ask. A ticket cannot raise this —
    contracts only shrink.
    """
    budget = patch_retry_budget(ticket)
    from koru.queue.contracts import contract_for_ticket

    contract = contract_for_ticket(project, ticket)
    if contract is not None and contract.max_attempts is not None:
        budget = min(budget, max(0, contract.max_attempts - 1))
    return budget


def _finish_patch_run(
    project: Path,
    ticket: dict,
    transaction: PatchTransactionResult,
    manifest: dict | None,
    attempts: list[dict],
    actor: str | None,
    authorize: Any,
) -> dict:
    return _finish_run(
        project,
        ticket,
        transaction,
        manifest,
        attempts,
        actor,
        _authorization_record(authorize),
    )


_READONLY_SCAN_ARTIFACT_NAMES = frozenset(
    {
        "analysis.toon.yaml",
        "analysis.toon",
        "duplication.toon.yaml",
        "duplication.yaml",
        "calls.yaml",
        "calls.toon.yaml",
        "map.toon.yaml",
        "project.toon.yaml",
    }
)


def _is_readonly_scan_artifact(rel_path: str) -> bool:
    norm = str(rel_path or "").replace("\\", "/").strip()
    while norm.startswith("./"):
        norm = norm[2:]
    norm = norm.lstrip("/")
    if not norm:
        return False
    basename = norm.rsplit("/", 1)[-1].lower()
    return basename in _READONLY_SCAN_ARTIFACT_NAMES


def _filter_readonly_scan_artifacts(paths: Any) -> tuple[str, ...]:
    if not paths:
        return ()
    return tuple(str(p) for p in paths if p and not _is_readonly_scan_artifact(str(p)))


def _perform_retry_call(
    llm_runner: Callable[[dict[str, Any], Path], CommandResult],
    action: dict[str, Any],
    base_prompt: str,
    project: Path,
    manifest: dict | None,
    outcome: PatchOutcome,
    enrich: Callable[[dict[str, Any], Path], dict[str, Any]] | None,
    *,
    previous_diff: str = "",
) -> CommandResult:
    retry_action = _build_retry_action(
        action, base_prompt, project, manifest, outcome, enrich,
        previous_diff=previous_diff,
    )
    res = llm_runner(retry_action, project)
    known = _filter_readonly_scan_artifacts(
        action.get("ticket_files") or (manifest or {}).get("touched_files") or ()
    )
    return wrap_reply_in_proposal_envelope(
        res,
        str(retry_action.get("prompt") or ""),
        project=project,
        known_files=known,
    )


class _AttemptDecision(NamedTuple):
    """What one judged attempt says to do next.

    ``done`` marks the run's final answer — ``result`` and ``outcome`` are what
    the caller receives. Otherwise ``result`` is the re-asked reply the next
    iteration will judge.
    """

    result: CommandResult
    outcome: PatchOutcome | None
    done: bool


@dataclass
class _PatchRun:
    """The state one ask-again run threads between attempts.

    The retry loop used to rebind a dozen locals every iteration — the budget
    left, the pinned base, the growing attempt record — which is precisely
    what made it a god function. Binding them here leaves the loop a straight
    line: judge, record, advance.
    """

    project: Path
    ticket: dict
    action: dict[str, Any]
    result: CommandResult
    llm_runner: Callable[[dict[str, Any], Path], CommandResult]
    enrich: Callable[[dict[str, Any], Path], dict[str, Any]] | None
    actor: str | None
    authorize: Any
    budget: int
    manifest: dict | None = None
    attempts: list[dict] = field(default_factory=list)
    base_prompt: str = ""
    remaining: int = 0
    verify_remaining: int = 0

    def __post_init__(self) -> None:
        raw_prompt = str(self.action.get("prompt") or "")
        known = _filter_readonly_scan_artifacts(
            (self.ticket.get("files") if isinstance(self.ticket, dict) else None)
            or self.action.get("ticket_files")
            or ()
        )
        ticket_id = str(self.ticket.get("id") or "") if isinstance(self.ticket, dict) else ""
        lessons_section = format_lessons_for_prompt(
            self.project, ticket_id=ticket_id or None, target_files=known,
        )
        self.base_prompt = f"{raw_prompt.rstrip()}\n\n{lessons_section}" if lessons_section else raw_prompt
        self.remaining = self.budget
        self.verify_remaining = verify_retry_budget(self.ticket if isinstance(self.ticket, dict) else None)
        # Producer side of the envelope contract: the bare diff the agent wrote
        # becomes a hash-bound ProposalEnvelope before the transaction judges it.
        self.result = wrap_reply_in_proposal_envelope(
            self.result,
            raw_prompt,
            project=self.project,
            known_files=known,
        )

    def record_attempt(self, transaction: PatchTransactionResult) -> None:
        """Fold one judged attempt into the run's permanent record."""
        self.attempts.append(
            _attempt_record(len(self.attempts) + 1, transaction, self.verify_remaining > 0)
        )

    def advance(self, transaction: PatchTransactionResult) -> _AttemptDecision:
        """Decide the run's next move after one judged attempt.

        Landing, a substantive failure, or an exhausted budget ends the run; a
        mechanical failure (or a verify failure when verify_remaining > 0) first
        pins the base (aborting on drift), then spends one budget unit re-asking
        the agent with the exact rejection attached.
        """
        outcome = transaction.outcome
        if outcome is None:
            return _AttemptDecision(transaction.result, outcome, True)
        is_verify = _is_verify_failure(outcome)
        if is_verify and outcome.code == VERIFY_BASELINE_FAILED:
            declared = _filter_readonly_scan_artifacts(
                (self.ticket.get("files") if isinstance(self.ticket, dict) else None) or ()
            )
            prev_touched = (
                set(diff_target_files(self.project, transaction.plan.diff))
                if (transaction.plan and transaction.plan.diff)
                else set()
            )
            if len(declared) <= 1 or set(declared).issubset(prev_touched):
                is_verify = False
        if is_verify:
            if self.verify_remaining <= 0:
                return _AttemptDecision(transaction.result, outcome, True)
        elif not outcome.retryable or self.remaining <= 0:
            return _AttemptDecision(transaction.result, outcome, True)
        # A structurally invalid model artifact gets one repair attempt. A
        # ticket/env knob may shrink that budget, never expand it into a loop.
        if outcome.code == NO_PATCH_EMITTED:
            self.remaining = min(self.remaining, 1)
        aborted = self._pin_or_abort(transaction)
        if aborted is not None:
            return _AttemptDecision(transaction.result, aborted, True)
        if is_verify:
            self.verify_remaining -= 1
        else:
            self.remaining -= 1
        prev_diff = transaction.plan.diff if (is_verify and transaction.plan) else ""
        result = _perform_retry_call(
            self.llm_runner, self.action, self.base_prompt, self.project,
            self.manifest, outcome, self.enrich,
            previous_diff=prev_diff,
        )
        return _AttemptDecision(result, outcome, result.returncode != 0)

    def _pin_or_abort(self, transaction: PatchTransactionResult) -> PatchOutcome | None:
        """Pin the base on the first failure, or abort if it has since drifted."""
        self.manifest, aborted = _pin_or_detect_drift(
            self.project, self.ticket, transaction.result, self.budget + self.verify_remaining,
            self.manifest, transaction, self.attempts,
        )
        return aborted


def apply_patch_with_retry(
    project: Path,
    result: CommandResult,
    ticket: dict,
    action: dict[str, Any],
    llm_runner: Callable[[dict[str, Any], Path], CommandResult],
    shell_runner: Callable[[str, Path], CommandResult],
    enrich: Callable[[dict[str, Any], Path], dict[str, Any]] | None = None,
    actor: str | None = None,
) -> tuple[CommandResult, PatchOutcome | None, dict | None]:
    """Apply the agent's patch, re-asking with the exact rejection on failure.

    A malformed or stale diff is a mechanical problem the agent can fix once it
    sees ``git apply``'s complaint, so those attempts are retried. A patch that
    applies but fails verification is a *substantive* failure — retrying it
    would just burn another agent run on the same wrong idea — so it is not.

    Returns the final reply, the final outcome, and the evidence bundle for the
    whole run — every attempt's patch hash included, so a retry can never make
    its predecessor disappear from the record.

    ``enrich`` re-attaches project context to the retry request; it is injected
    rather than imported so this module stays independent of the queue runner.
    """
    # Imported at call time so the facade stays the single seam tests stub.
    from koru.queue.authorization import build_authorizer
    from koru.queue.transaction.service import execute_patch_transaction

    run = _PatchRun(
        project=project,
        ticket=ticket,
        action=action,
        result=result,
        llm_runner=llm_runner,
        enrich=enrich,
        actor=actor,
        authorize=build_authorizer(project, ticket, actor or "koru-shell"),
        budget=_contract_capped_budget(project, ticket),
    )

    while True:
        transaction = execute_patch_transaction(
            project, run.result, ticket, shell_runner, run.manifest,
            authorize=run.authorize,
        )
        run.record_attempt(transaction)
        decision = run.advance(transaction)
        if decision.done:
            return decision.result, decision.outcome, _finish_patch_run(
                project, ticket, transaction, run.manifest, run.attempts,
                run.actor, run.authorize,
            )
        run.result = decision.result


def _pin_or_detect_drift(
    project: Path,
    ticket: dict,
    result: CommandResult,
    budget: int,
    manifest: dict | None,
    transaction: PatchTransactionResult,
    attempts: list[dict],
) -> tuple[dict | None, PatchOutcome | None]:
    """Pin the base on the first failure, or abort if it since drifted.

    Pinning happens under the run_id the transaction already used, so every
    manifest and the evidence of this run share one directory. Every later
    attempt is judged against that same snapshot, so a retry can never
    silently rebase onto a workspace another session has moved in the
    meantime.
    """
    if manifest is None:
        manifest = _pin_base(
            project,
            ticket,
            result,
            budget,
            run_id=transaction.plan.run_id if transaction.plan else None,
        )
        persist_manifest(project, manifest)
        return manifest, None

    drift = manifest_drift(project, manifest)
    if not drift:
        return manifest, None

    aborted = PatchOutcome(
        code=MANIFEST_MISMATCH,
        message=(
            "the workspace changed between patch attempts, so the retry was "
            f"abandoned rather than rebased onto a moving target ({drift}). "
            "Re-run the ticket against the new state."
        ),
    )
    attempts.append(
        patch_attempt_record(
            len(attempts) + 1,
            patch_sha256=None,
            outcome_code=aborted.code,
            message=aborted.message,
        ),
    )
    return manifest, aborted


def _build_retry_action(
    action: dict[str, Any],
    base_prompt: str,
    project: Path,
    manifest: dict | None,
    outcome: PatchOutcome,
    enrich: Callable[[dict[str, Any], Path], dict[str, Any]] | None,
    *,
    previous_diff: str = "",
) -> dict[str, Any]:
    # git and test output can quote file contents, so redact before it
    # travels back out to the model.
    diagnostic = redact_secrets(outcome.diagnostics or outcome.message)
    touched = _filter_readonly_scan_artifacts((manifest or {}).get("touched_files") or ())
    if _is_verify_failure(outcome):
        prev_touched = set(diff_target_files(project, previous_diff)) if previous_diff else set()
        missing = tuple(f for f in touched if f not in prev_touched) if len(touched) > 1 else ()
        prompt = build_verify_retry_prompt(
            base_prompt,
            diagnostic,
            previous_diff=previous_diff,
            missing_files=missing,
        )
    else:
        prompt = build_retry_prompt(base_prompt, diagnostic)
    if manifest and (
        outcome.code in (PATCH_DOES_NOT_APPLY, NO_PATCH_EMITTED)
        or _is_verify_failure(outcome)
    ):
        # Safe only because the manifest guarantees these contents are still
        # the ones the patch must apply to.
        prompt += current_file_excerpt(project, touched)
    retry_action = {**action, "prompt": prompt}
    if enrich is not None:
        retry_action = enrich(retry_action, project)
    return retry_action


def _distill_lesson_rule(outcome_code: str | None, diagnostic: str, self_repaired: bool) -> str:
    diag_line = next((ln.strip() for ln in (diagnostic or "").splitlines() if ln.strip()), "")[:240]
    if self_repaired:
        return f"Recovered after initial '{outcome_code}': ensure hunks match disk context and pass verification ({diag_line})."
    if outcome_code == "patch_destructive_truncation":
        return "Do not delete existing public functions/classes or truncate large sections of the module unless explicitly replacing them."
    if outcome_code == "patch_introduces_antipattern":
        return f"Avoid introducing performance or resource-leak anti-patterns ({diag_line})."
    if outcome_code in (VERIFY_FAILED_ISOLATED, VERIFY_FAILED_ROLLED_BACK, VERIFY_BASELINE_FAILED):
        return f"Verification failed ({diag_line}); preserve existing public signatures, imports, and test expectations."
    if outcome_code == PATCH_DOES_NOT_APPLY:
        return f"Patch context did not match disk ({diag_line}); include exact 3-line context from current file contents."
    return f"Previous attempt failed with '{outcome_code}': {diag_line}"


def record_run_lesson(
    project: Path,
    ticket: dict,
    bundle: dict,
    transaction: PatchTransactionResult,
) -> dict | None:
    """Persist a structured post-mortem lesson when a run fails or self-repairs."""
    import json
    from datetime import datetime, timezone

    attempts = bundle.get("patch_attempts") or []
    verdict = str(bundle.get("verdict") or "")
    outcome = transaction.outcome
    failed_attempts = [a for a in attempts if a.get("outcome") and a.get("outcome") != "landed"]
    if verdict == VERDICT_VERIFIED and not failed_attempts:
        return None
    first_fail = failed_attempts[0] if failed_attempts else {}
    outcome_code = str(
        (outcome.code if outcome else None)
        or first_fail.get("outcome")
        or "unknown_failure"
    )
    diagnostic = redact_secrets(
        (outcome.diagnostics or outcome.message)
        if outcome is not None
        else str(first_fail.get("message") or ""),
        limit=500,
    )
    self_repaired = verdict == VERDICT_VERIFIED and bool(failed_attempts)
    plan = transaction.plan
    raw_targets = (
        list(plan.targets)
        if plan and plan.targets
        else list((ticket.get("files") if isinstance(ticket, dict) else None) or [])
    )
    targets = list(_filter_readonly_scan_artifacts(raw_targets))
    lesson = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": bundle.get("run_id"),
        "ticket_id": str(ticket.get("id") or "") if isinstance(ticket, dict) else "",
        "project": project.name,
        "verdict": verdict,
        "self_repaired": self_repaired,
        "outcome_code": outcome_code,
        "failed_codes": [str(a.get("outcome")) for a in failed_attempts if a.get("outcome")],
        "target_files": targets,
        "diagnostic": diagnostic,
        "rule": _distill_lesson_rule(outcome_code, diagnostic, self_repaired),
    }
    line = json.dumps(lesson, ensure_ascii=False, sort_keys=True) + "\n"
    try:
        lessons_dir = project / ".koru"
        lessons_dir.mkdir(parents=True, exist_ok=True)
        with (lessons_dir / "lessons.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass
    fleet_path = (os.environ.get("KORU_FLEET_LESSONS_PATH") or "").strip()
    if fleet_path:
        try:
            fp = Path(fleet_path)
            fp.parent.mkdir(parents=True, exist_ok=True)
            with fp.open("a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            pass
    return lesson


def _read_bounded_tail_lines(path: Path) -> list[str]:
    max_bytes = 65536
    if not path.is_file():
        return []
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > max_bytes:
                fh.seek(size - max_bytes)
                raw = fh.read()
                nl = raw.find(b"\n")
                if nl != -1:
                    raw = raw[nl + 1 :]
            else:
                raw = fh.read()
        return raw.decode("utf-8", errors="replace").splitlines()
    except OSError:
        return []


def load_project_lessons(
    project: Path,
    *,
    ticket_id: str | None = None,
    target_files: Any = None,
    limit: int = 5,
) -> list[dict]:
    """Load recent relevant lessons from ``.koru/lessons.jsonl`` (bounded read)."""
    import json

    candidates: list[Path] = [project / ".koru" / "lessons.jsonl"]
    fleet_path = (os.environ.get("KORU_FLEET_LESSONS_PATH") or "").strip()
    if fleet_path:
        candidates.append(Path(fleet_path))
    target_set = set(_filter_readonly_scan_artifacts(target_files or ()))
    matched: list[dict] = []
    seen_rules: set[str] = set()
    for path in candidates:
        for raw_line in reversed(_read_bounded_tail_lines(path)):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                item = json.loads(raw_line)
            except ValueError:
                continue
            if not isinstance(item, dict):
                continue
            same_ticket = bool(ticket_id and item.get("ticket_id") == ticket_id)
            item_files = set(item.get("target_files") or ())
            same_files = bool(target_set and (target_set & item_files))
            is_self_repaired = bool(item.get("self_repaired"))
            if not (same_ticket or same_files or is_self_repaired):
                continue
            rule = str(item.get("rule") or "").strip()
            if not rule or rule in seen_rules:
                continue
            seen_rules.add(rule)
            matched.append(item)
            if len(matched) >= max(1, limit):
                return matched
    return matched


def format_lessons_for_prompt(
    project: Path,
    *,
    ticket_id: str | None = None,
    target_files: Any = None,
    limit: int = 5,
) -> str:
    """Format relevant past lessons into a concise prompt guardrail section."""
    lessons = load_project_lessons(
        project, ticket_id=ticket_id, target_files=target_files, limit=limit,
    )
    if not lessons:
        return ""
    bullets = [f"- [{item.get('outcome_code', 'lesson')}] {item.get('rule', '')}" for item in lessons]
    return (
        "## Learned Constraints from Previous Runs\n\n"
        "Apply these lessons distilled from earlier attempts on this ticket/files:\n"
        + "\n".join(bullets)
    )


def _attempt_record(
    attempt: int,
    transaction: PatchTransactionResult,
    verify_retryable: bool,
) -> dict:
    """One transaction attempt, as it will be remembered."""
    plan = transaction.plan
    outcome = transaction.outcome
    record = patch_attempt_record(
        attempt,
        patch_sha256=(
            hashlib.sha256(plan.diff.encode("utf-8")).hexdigest() if plan else None
        ),
        outcome_code=outcome.code if outcome else None,
        message=outcome.message if outcome else "",
        retryable=bool(
            outcome
            and (outcome.retryable or (verify_retryable and _is_verify_failure(outcome)))
        ),
    )
    # A retry can land on a different provider after a fallback; each attempt
    # remembers who authored it, not just the bundle-level summary.
    provenance = provenance_from_result(transaction.result)
    if provenance:
        record["provider"] = provenance.get("provider")
        record["model"] = provenance.get("model")
    return record


def _authorization_record(authorize) -> dict | None:
    """What the last authorize() call actually granted, or None when legacy."""
    record = getattr(authorize, "record", None)
    return dict(record) if record else None


def _build_verify_record(plan: Any, ticket: dict, outcome: PatchOutcome | None) -> dict:
    if not plan:
        return {}
    return {
        "command": plan.verify_command,
        "source": plan.verify_source,
        "profile": str((ticket.get("inputs") or {}).get("verify_profile") or "") or None,
        "status": _verify_status(plan, outcome),
    }


def _build_promotion_record(project: Path, plan: Any, run_id: str, outcome: PatchOutcome | None) -> dict:
    if not plan:
        return {}
    promotion: dict = {"mode": plan.mode, "isolated": plan.isolated}
    if plan.mode == PROMOTION_BRANCH and outcome is None:
        branch = f"koru/run-{run_id}"
        promotion["branch"] = branch
        # The ref can be moved later; the recorded SHA cannot.
        promotion["commit_sha"] = branch_head(project, branch) or None
    return promotion


def _finish_run(
    project: Path,
    ticket: dict,
    transaction: PatchTransactionResult,
    manifest: dict | None,
    attempts: list[dict],
    actor: str | None = None,
    authorization: dict | None = None,
) -> dict:
    """Assemble and persist the run's evidence bundle.

    A failed write does not raise: the bundle is still returned, and the
    completion gate — which judges the *persisted* copy — will refuse to close
    the ticket, which is the correct consequence of unprovable success.
    """
    plan = transaction.plan
    frozen = manifest or transaction.manifest
    run_id = str(
        (frozen or {}).get("run_id")
        or (plan.run_id if plan else None)
        or uuid4().hex[:12],
    )
    outcome = transaction.outcome
    verify = _build_verify_record(plan, ticket, outcome)
    promotion = _build_promotion_record(project, plan, run_id, outcome)

    bundle = build_evidence_bundle(
        run_id=run_id,
        ticket=ticket,
        manifest=frozen,
        patch_attempts=attempts,
        verify=verify,
        promotion=promotion,
        verdict=_verdict(plan, outcome),
        actor=actor,
        provenance=provenance_from_result(transaction.result),
        bindings=plan.proposal if plan else None,
        authorization=authorization,
    )
    try:
        persist_evidence(project, bundle)
    except OSError:
        pass
    try:
        record_run_lesson(project, ticket, bundle, transaction)
    except Exception:
        pass
    _journal_terminal(project, run_id, bundle, transaction)
    return bundle


def _journal_terminal(
    project: Path,
    run_id: str,
    bundle: dict,
    transaction: PatchTransactionResult,
) -> None:
    """Close the run's journal with its verdict.

    Refusals were journaled by the transaction as they happened, and artifact
    delivery writes its own ``completed`` — only a landed patch still owes the
    journal its terminal event. Best-effort by design: the journal aids
    recovery, while the completion *gate* is the evidence bundle.
    """
    plan = transaction.plan
    if transaction.outcome is not None or plan is None or plan.mode == PROMOTION_ARTIFACT:
        return
    try:
        RunJournal(project, run_id).append(
            PHASE_COMPLETED, data={"verdict": bundle["verdict"]},
        )
    except OSError:
        pass


def _verify_status(plan: PatchPlan, outcome: PatchOutcome | None) -> str:
    """What happened at the gate: passed, failed, or never ran."""
    if not plan.verify_command:
        return "skipped"
    if outcome is None:
        return "passed" if plan.mode != PROMOTION_ARTIFACT else "skipped"
    return "failed" if outcome.code.startswith("verify") else "not_reached"


def _verdict(plan: PatchPlan | None, outcome: PatchOutcome | None) -> str:
    if outcome is not None or plan is None:
        return VERDICT_REFUSED
    if plan.mode == PROMOTION_ARTIFACT:
        return VERDICT_ARTIFACT
    return VERDICT_VERIFIED if plan.verify_command else VERDICT_APPLIED


def _pin_base(
    project: Path,
    ticket: dict,
    result: CommandResult,
    budget: int,
    run_id: str | None = None,
) -> dict:
    """Freeze the base the remaining attempts must target.

    The first attempt is pinned precisely when it failed for a reason that still
    let us read its targets. A corrupt diff yields none — ``git apply
    --numstat`` cannot parse it — which is exactly the case retries exist for,
    so fall back to the files the ticket declared. A manifest that pins nothing
    would silently permit the rebase it is meant to prevent.
    """
    from koru.queue.verify.resolver import resolve_verify

    known = _filter_readonly_scan_artifacts(ticket.get("files") or ())
    diff = extract_unified_diff(result.stdout, project=project, known_files=known) or ""
    diff_targets = diff_target_files(project, diff)
    declared_targets = tuple(str(rel) for rel in (ticket.get("files") or []))
    merged_targets = tuple(dict.fromkeys((*diff_targets, *declared_targets)))
    raw_targets = merged_targets or diff_targets or declared_targets
    targets = _filter_readonly_scan_artifacts(raw_targets) or raw_targets
    return build_manifest(
        project,
        run_id=run_id or uuid4().hex[:12],
        ticket=ticket,
        diff=diff,
        targets=targets,
        verify_command=resolve_verify(project, ticket, targets).command,
        mode=promotion_mode(ticket),
        attempt=1,
        max_attempts=budget + 1,
    )


execute_with_patch_retries = apply_patch_with_retry
