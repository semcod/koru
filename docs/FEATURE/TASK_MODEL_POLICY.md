---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "task-model-policy",
  "kind": "feature",
  "version": 1,
  "title": "Dynamic task model policy and LLM routing",
  "status": "implemented",
  "owner": "semcod/koru",
  "scope": "repository",
  "updated": "2026-09-27",
  "source_revision": "2c82e2055feb269399c3081ec6750e5b5ee9b7df",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/koru/commit/2c82e2055feb269399c3081ec6750e5b5ee9b7df",
    "https://github.com/semcod/koru/blob/main/src/koru/task_model_policy.py"
  ]
}
---

# Dynamic task model policy and LLM routing

<!-- docs:section summary -->
## Summary

Koru 0.1.461 implements an automated task model policy (`src/koru/task_model_policy.py`) that classifies tickets by structural complexity and routes them to appropriate LLM tiers, optimizing token expenditure and delivery velocity.

<!-- docs:section details -->
## Details

The routing engine classifies queued tasks into two primary model categories:

1. **Simple and bounded tasks (Fast Tier)**: Single-file edits, localized lint or type fixes, documentation formatting, and small unit test updates are routed to lightweight, high-throughput models (e.g. `zai/glm-5.3-flash` or `gemini-3.8-flash`). Environment variable `KORU_TILLM_SIMPLE_MODEL` configures this target.
2. **Complex and structural tasks (Reasoning Tier)**: Tickets matching profiles like `god_module_split`, `cc_hotspot_refactor`, `god_function_refactor`, multi-file dependency boundaries, and governance reconciliation are routed to high-capacity reasoning models (`glm-5.3`, `claude-code`, or `opencode`).
3. **Task profiles integration**: Complexity heuristics inspect target file counts, cyclomatic complexity deltas, and task profile labels in `task_profiles.yaml`.
4. **Fallback logic**: If a lightweight model execution fails verification, retry logic escalates the ticket to the reasoning tier.

<!-- docs:section validation -->
## Validation

Routing behavior is verified through automated and operational checks:
- Conformance tests: `pytest tests/test_task_model_policy.py` validates heuristic score thresholds and model assignment matrices.
- Operational logs: `koru queue` logs output `corr=operator-model-routing` events displaying ticket ID, complexity classification, and selected model backend.

<!-- docs:section risks -->
## Risks

- **Misclassification**: Deep structural bugs masquerading as single-line syntax fixes may exhaust retries on flash models before escalation.
- **Provider rate limits**: High throughput on fast tier may trigger HTTP 429 rate limits, handled via backoff and provider rotation.
- **Next steps**: Introduce token budget tracking per ticket to adjust routing dynamically based on remaining project quota.
