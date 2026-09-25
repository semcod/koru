# Ticket 177: Gate fleet scan ticket creation with pinned Autonom admission

- **ID**: ticket-177
- **Owner**: bot:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-19

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: workspace PLF-001 and Autonom STARTER-017;
Koru Planfile STARTER-731. User requests worktrees then PRs then new issues.
Application scope is disjoint from active tickets172/175/176. Own isolated
checkout and revision1/fencing1 lease; no existing owner's lease reclaimed.

Apply the exact published Autonom evaluator at the Koru scan apply boundary.
Operator opts fleet instances in through KORU_FLEET_ADMISSION_ENABLED=1 or either
configuration variable. Pin configuration and evaluator SHA-256. Map canonical
project paths explicitly to repository/base/runtime pins; never infer identity.
Reject missing, stale, partial, malformed or unknown evidence without ticket
creation. Keep ordinary standalone mode, read-only scanning and existing queue
continuation unchanged. Admit at most one new suggestion per fleet scan.
Expose the admission observation in the scan result, without granting execution,
lease or publication authority. Source publication and deployment are separate.

## Acceptance criteria

- [x] AC-01: Pinned evaluation denies invalid input and preserves identity/authority boundaries.
- [x] AC-02: Scan denial creates no ticket; permitted fleet scan emits at most one suggestion; read-only and standalone paths preserved.
- [x] AC-03: Focused tests and required governance checks pass.
- [ ] AC-04: Independent protected publication, pilot deployment readback and source worktree cleanup.

## Bounds

Four implementation/test files, one application component. No dependency,
policy, registry, protected controller or runtime authority changes. Exact
Autonom source94080c91a628b97d2416b4114f1dec1f11cf2880;
SHA256 07d7410be09ddd7b24f73171a5ddd2980bcd4dbffb85a49007ae762dab0450d6.

Validation: 129 focused/scan/phase regression tests passed with governance enabled; five native subprocess contract cases passed using exact published Autonom bytes. Ruff and diff checks passed. Source publication and pilot deployment remain pending.
