# Ticket 009 evidence

## Data flow

1. Discovery creates a Planfile ticket and project-owned capability contract.
2. Ticket translation assembles messages and project context, excluding
   secrets, generated artifacts and out-of-project paths.
3. SubLLM resolves either `koru-agent/planning-assistant` or
   `koru-agent/queue-executor`; both have one candidate: Cursor `grok-4.6`
   with `effort=xhigh` and `fast=false`.
4. The Cursor SDK runs locally with `tools=[]`, so the model returns text but
   cannot mutate the checkout.
5. Queue patch parsing, path policy, baseline comparison, isolated worktree
   application, verification and promotion remain deterministic Koru steps.

## Live evidence

| Route | Result | Duration | Usage | Shape |
|---|---:|---:|---:|---|
| `queue-executor` | finished | 6,462 ms | 3,685 total / 102 reasoning | valid target-bound unified diff |
| `planning-assistant` | finished | 8,943 ms | 3,552 total / 213 reasoning | valid JSON with all requested keys |

Both runs reported model `grok-4.6` and parameters
`{"effort":"xhigh","fast":"false"}`. Neither run exposed write tools.

## Limits

Removed Koru-enforced defaults:

- no monetary budget blocks planning;
- no `max_tokens` field is sent to Cursor;
- no 32,000-character default truncation;
- no 12-file default context slice.

Retained operational safeguards:

- SDK and subprocess timeouts;
- bounded retries and autonomous iterations;
- provider context, rate and entitlement limits;
- explicit per-ticket context caps when requested;
- context path and secret exclusions;
- patch path policy, clean baselines, isolated verification and promotion
  rules.

The discovery scaffold still carries a legacy `llm_max_tokens=4000` metadata
field for old Planfile readers. Hydration removes it, request translation does
not emit it, and the Cursor transport cannot send it.

## Historical comparison

Historical Koru paths selected Qwen3 Coder Next for OpenRouter planning and
GPT-4o Mini for ordinary OpenRouter queue execution. They also had independent
HTTP/vendor transports, cost guards and request truncation. The new evidence
shows one policy-controlled transport, exact model parameters, valid JSON and
valid diff output.

No new A/B request was sent to either prohibited historical model. Therefore
the comparison supports transport, policy and output-shape conclusions, not a
statistically controlled quality or latency ranking.

## Validation

- affected tests: 242 passed;
- governance and diff checks: passed;
- affected Ruff checks: passed;
- complete suite: 3,586 passed, 25 skipped, 159 deselected and 939 subtests;
  one ticket-related environment expectation was corrected;
- two unrelated baseline failures remain:
  `test_pyproject_metadata.py::test_base_runtime_dependencies_stay_small` and
  `test_volume_reduction_plan.py::test_current_index_header_is_parseable_and_structural_volume_does_not_regress`;
- repository-wide Ruff has 32 pre-existing import-order findings outside this
  ticket's allowed paths.
