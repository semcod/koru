# Koru autonomy assessment — September 2026

Assessment date: 2026-09-05. Source baseline:
`c695361224afbdd13dda6be89d6862a70300ee09` (PR #114).
Scope: repository source inspection and deterministic regression tests.
This assessment does not measure live IDE/LLM completion rates.

## Implemented controls and their boundaries

Koru already implements planning, bounded retries, leased queue execution,
patch transactions, signed execution grants and evidence collection. The next
refactor should connect and clarify these controls rather than create parallel
implementations of them.

| Boundary | Source | Observed behavior |
| --- | --- | --- |
| Planning | `src/koru/autonomy/execution_plan.py` | Existing `koru.execution_plan/v1` compiles strategy, signals and task profiles. |
| IDE decision | `src/koru/autonomy/decision_arbiter.py` | Cooldowns and failing test signals veto drive; verdicts produce action plans. |
| Queue completion | `src/koru/queue/runner.py` | Verification errors prevent completion; ordinary zero-exit shell work may finish without a separate test profile. |
| Patch authorization | `src/koru/queue/authorization.py` | Contracts and optional signed grants bind the frozen patch plan; absence of both retains legacy behavior. |
| Replay protection | `src/koru/queue/grant_store.py` | Grant JTI claims already exist; applicability depends on using the grant-enabled transaction path. |
| Post-run verification | `src/koru/autonomy/post_run_verify.py` | Optional commands run after done; failures reopen or block tickets. |
| Expired work | `src/koru/autonomy/ide_work.py` | Expired leases block tasks and project waiting_human_triage with sla:urgent. |

## Confirmed issues to prioritize

1. `assess_verdict` is a heuristic score. Git changes and chat activity can
   produce `completed` even when test status is unknown. The arbiter can emit
   `close_ticket`; the inspected post-drive function stores and emits that
   plan, without executing ticket closure. A future dispatcher must require
   bound verification evidence before interpreting that action as authority.
2. Post-run verification is disabled by default and requires nonempty commands.
   Its stock subprocess runner has no timeout. Its successful-ticket cache is
   keyed by ticket ID, not HEAD or attempt. These boundaries need explicit
   completion, deadline and invalidation contracts.
3. The old roadmap says manifests, grants and JTI protection are absent. The
   queue patch implementation already contains these controls. Remaining work
   is coverage and lifecycle unification across execution paths.
4. Historical post-run documentation describes reopening stale work, whereas
   current lease expiry escalates to human triage. Operating instructions must
   describe that behavior accurately.

## Validation

Test execution and bounded refactoring acceptance criteria are being recorded
for this assessment. No runtime behavior is changed by the documentation work.
