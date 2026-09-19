```dsl
# Deterministic evidence for autonomous continuation; not merge approval.
DECISION D-142-0001
TICKET ticket-142
HEAD_SHA e63b83ca5eadd9b83a8fe1efba27b14dce7c47f8
CORRELATION_ID koru-ticket-142-autonomy-20260915
ACTOR agent:codex
APPLIED_RULE C-CONCURRENCY-001
INPUT candidate_ticket = "ticket-142"
INPUT candidate_route = "ASSIST_READ_ONLY"
INPUT overlapping_ticket = "ticket-065"
INPUT overlapping_ticket_status = "IN_PROGRESS"
INPUT overlapping_path = ".governance/manifest.json"
INPUT stale_active_ticket = "ticket-128"
INPUT stale_active_ticket_status = "IN_PROGRESS/PUBLICATION"
INPUT stale_active_ticket_pr = "none"
INPUT taskand_delivery = "ACTIVE_TICKET_REQUIRED"
INPUT autonom_cycle = "proposals-only"
INPUT protected_controller = "BLOCKED:protected_registry_profile_invalid:wellmanifest/dsl"
INPUT validator_preflight = "CONFIGURATION_CHECKED"
INPUT onedev_head = "a960a6960d4b086b494a9b78502a9ceda6f7a24d"
INPUT onedev_status = "FAILURE:GOV-TICKET-001"
INPUT staged_gate = "FAIL:GOV-ARCHITECTURE-001,GOV-BASE-002,GOV-BUDGET-001,GOV-INTEGRATION-001,GOV-SCOPE-001,GOV-WORKSTREAM-003"
INPUT expected_verdict_from_rule = "BLOCKED"
VERDICT BLOCKED AUTHORITY DETERMINISTIC
REJECTED PUBLISH_OR_MERGE_TICKET_142 BECAUSE ticket-065 owns an overlapping shared contract path and its exact-head protected check is failed
ASSERT PRESERVE_TICKET_065_WORKTREE_AND_PR
ASSERT DO_NOT_TAKE_OVER_FOREIGN_WORKTREE
ASSERT RECHECK_WORK_START_AND_EXACT_HEAD_AFTER_TICKET_065_TERMINAL_RECEIPT
ASSERT USE_TASKAND_DELIVER_PLAN_AND_AUTONOM_CYCLE_BEFORE_RETRY
ASSERT PROTECTED_VALIDATOR_REMAINS_THE_ONLY_MERGE_AUTHORITY
# Future route: observe ticket/worktree, run publisher preflight, run
# taskand/autonom observation, then continue only the authorized ticket or
# route to ASSIST_READ_ONLY/BLOCKED. Never repeat an unchanged failed effect,
# invent approval, or merge another ticket.
```
