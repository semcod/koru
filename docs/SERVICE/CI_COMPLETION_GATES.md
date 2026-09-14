---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "ci-completion-gates",
  "kind": "service",
  "version": 1,
  "title": "CI and completion gates",
  "status": "implemented",
  "owner": "semcod/koru",
  "scope": "repository",
  "updated": "2026-09-14",
  "source_revision": "e7b3fa24433dcfd85261eeb570c698ab0ac904b3",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/koru/commit/e7b3fa24433dcfd85261eeb570c698ab0ac904b3"
  ]
}
---

# CI and completion gates

<!-- docs:section summary -->
## Purpose and status

Configure project CI and completion checks explicitly. A successful queue handler alone does not prove that every required gate ran.

<!-- docs:section details -->
## Scope and behavior

`koru ci run --project .` runs the policy CI command followed by topology quality gates. `koru ci gates --project .` runs only quality gates. `--skip-gates` omits topology checks and is not evidence of full CI success.

Configure `.planfile/.koru/policy.yaml` for the target project:

```yaml
ci:
  command: bash scripts/ci-test.sh
  timeout_seconds: 600
llm:
  require_ci_pass_before_complete: true
```

The referenced script must exist and implement the project's checks. Configure quality gates separately in `.koru/topology.yaml`; typical tools are regix and redup. Keep thresholds and command definitions consistent with CI.

`when.before_complete_ticket.commands` in `koru.yaml` provides autonomous pre-completion verification hooks. Ordinary `when:` briefing sections are not equivalent. [Post-run verification](POST_RUN_VERIFICATION.md) is an additional check after completion, not a replacement for pre-completion requirements.

See [execution surfaces](COMMAND_EXECUTION.md) and [autopilot setup](../autopilot-quickstart.md) for the surrounding workflow.

<!-- docs:section validation -->
## Validation

Inspect policy, topology and referenced scripts before execution. Run `koru ci run --project .` only when its configured commands are authorized. Preserve its exit status and check that both policy and quality-gate stages ran.

Regression coverage: `python -m pytest tests/test_ci_pipeline.py`. For a missing CI command, fix project policy; for threshold differences, compare local topology with CI configuration.

<!-- docs:section risks -->
## Risks and ownership

CI commands can change files or contact external services. Review them before running. Do not mark a ticket complete on the basis of skipped gates, a partial command, or a log message without successful execution evidence.
