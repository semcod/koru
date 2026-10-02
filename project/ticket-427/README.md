# Ticket 427: Protected repository admission client

- **ID**: ticket-427
- **Owner**: codex-admission-client
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-02

SESSION_EXECUTION_AUTHORIZATION: the user explicitly supplies admission and requests continued repair, deployment and independent publication. Operator policy may admit this exact native allocation; it does not replace independent review.

## Acceptance criteria

- [x] AC-01: Koru verifies external transport/configuration pins, TLS identity and principal credential without logging secrets.
- [x] AC-02: Acquisition/check responses bind the exact native intent and current authoritative lease; stale, forged, expired and unavailable admission denies.
- [x] AC-03: An operator-authorized live controller can admit this native worktree over verified HTTPS.
- [ ] AC-04: Native gates, focused tests and independent OneDev/Validator publication pass.

The client is an admission API for execution adapters, not a grant to use legacy staging or publish without independent validation.

## Consumer contract

Use `AdmissionClient(config_path, independently_accepted_config_sha256, registered_primary)` with external configuration containing the HTTPS origin, CA certificate path and digest, a private credential file, the expected policy digest, authority reference and principal actor. `acquire(request)` returns the authoritative editing lease. `check(request, receipt)` performs a fresh authenticated check and rejects changed revision/fencing, expired authority or changed target/configuration. The request uses the Autonom repository-admission request schema.

The module CLI accepts `--config`, `--config-sha256`, `--primary`, `--request` and optionally `--check-receipt`. It never accepts a credential on argv, follows redirects, uses environment proxies or disables certificate verification. Configuration generation and policy approval belong to the operator/control deployment.

Execution adapters must enforce the accepted intent scope and check before every effect. This client grants neither legacy temporary staging nor commit/push/merge; the standing dispatcher and protected publication state machine remain separate integration work.
