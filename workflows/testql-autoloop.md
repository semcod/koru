---
description: testql autonomous stabilization loop for MCP-driven development
---
# TestQL Autoloop (MCP)

Use this workflow to run an iterative loop: discover -> generate -> run -> analyze -> refactor -> re-run,
until quality gates are stable.

1. Validate local environment and tools.
   - `testql --version`
   - `pyqual --help`
   - `curl -sf http://localhost:8101/health || true`
   - `curl -sf http://localhost:8100 || true`
   - `curl -sf http://localhost:8105/status || true`

2. Initialize state if missing.
   - Ensure `.testql/autoloop-state.json` exists.
   - Set `iteration=0`, `status="running"`, and empty `metrics_history`.

3. Build/update topology context.
   - `testql topology --format json > .testql/topology.json`
   - Optionally extend with sitemap if frontend is reachable.

4. Select next focus area.
   - Pick the highest-priority route/module by failure frequency, criticality, and topology impact.
   - Write chosen target into `current_focus` in `.testql/autoloop-state.json`.

5. Generate focused scenarios.
   - `mkdir -p .testql/generated`
   - `testql generate . --output-dir .testql/generated --format testql`
   - If focus is specific, generate or edit only matching scenario files.

6. Execute scenarios and collect report.
   - `mkdir -p .testql/reports`
   - `testql run examples/testtoon-basics/minimal.testql.toon.yaml --dry-run --quiet --output json > .testql/reports/iteration.json`
   - For GUI-only fallback, run with environment-appropriate commands.

7. Run quality gates.
   - `pyqual run`
   - Capture metrics: coverage, vallm_pass, cc_max, fail_rate, flaky_rate.

8. Produce strict LLM decision JSON.
   - Save decision payload to `.testql/reports/llm-decision.json`.
   - Validate it against `.testql/schemas/llm-decision.schema.json`.

9. Apply one scoped refactor batch.
   - If `decision=fix_code` or `fix_test`, change only the selected focus area.
   - Re-run Step 6 and Step 7 after changes.

10. Decide whether to continue or stop.
   - Stop when all are true:
     - no critical failures in last 2 iterations
     - coverage >= 65
     - vallm_pass >= 60
     - cc_max <= 10
   - Otherwise increment iteration and repeat from Step 3.

11. Finalize stabilization report.
   - Write summary to `.testql/reports/stabilization-summary.md`.
   - Include: iterations, fixed issues, deferred blockers, next refactor targets.
