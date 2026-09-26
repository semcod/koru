# Ticket 262: Decompose run_taskand_request in queue runners to reduce cyclomatic complexity

- **ID**: ticket-262
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Refactor `run_taskand_request` in `src/koru/queue/runners.py` to reduce its
cyclomatic complexity from 47 (code2llm/radon, limit 15) down to single digits,
while keeping 100% backward-compatible behavior for the gateway orchestrator,
gateway proc-call and local CLI fallback paths.

1. Extract `_taskand_gateway_config` to resolve gateway URL, timeout and auth headers
   (returned as the `_TaskandGatewayConfig` NamedTuple).
2. Extract `_probe_taskand_gateway` for the `/healthz` availability probe.
3. Extract `_taskand_gateway_target` to resolve the endpoint/body for plan vs uri
   modes (returned as the `_TaskandGatewayTarget` NamedTuple).
4. Extract `_orchestrator_taskand_result` and `_proc_call_taskand_result` to map
   the two gateway reply shapes behind `_parse_taskand_gateway_payload`, sharing
   the `_TaskandReplyContext` NamedTuple instead of a five-parameter clump.
5. Extract `_post_taskand_gateway` for the POST call, delegating to
   `_read_taskand_reply`, `_taskand_http_error_result` and
   `_taskand_url_error_result`.
6. Extract `_run_taskand_cli_call` for the local CLI fallback invocation.
7. Keep `run_taskand_request` a compact strategy dispatcher (radon CC 47 -> 7).
8. Add regression tests for the previously uncovered branches: missing uri/plan
   (400), gateway+CLI unavailable (503), failed orchestrator run, CLI invalid
   JSON output.

Authorization: SESSION_EXECUTION_AUTHORIZATION — planfile ticket PLF-039
(code2llm cc signal, high priority) handed this decomposition to this session
with instructions to implement, run local regression gates and close the
planfile ticket.

## Acceptance criteria

- [ ] AC-01: All tests in `tests/test_queue_runners.py` and `tests/test_taskand_runner.py` pass.
- [ ] AC-02: `run_taskand_request` cyclomatic complexity drops from 47 to <=7 (radon) and no extracted taskand helper exceeds 11.
- [ ] AC-03: code2llm re-run reports no function above the cc limit 15 in `src/koru/queue/runners.py`.
- [ ] AC-04: `ruff check` reports zero errors for the touched files.
- [ ] AC-05: `bash project/governance-check.sh` reports 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
