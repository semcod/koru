---
participant-id: agent:codex
role: agent
ticket: ticket-001
responseRequiredFrom:
  - unresolved:human
---

# Participant: Codex

## Understanding

The current todo2code prototype discovers useful work correctly but excludes
project communication and has a direct self-approved patch path outside Koru's
transaction. It also lacks ownership guards for governance ticket files.

## Approved plan

1. Enable deterministic project communication in todo2code discovery.
2. Add fail-closed governance path and output-location guards.
3. Make human execution the default and forbid implicit human-to-LLM promotion.
4. Route fully diffed source patches through Koru's manifest transaction or
   refuse them when authorization/verification cannot be established.
5. Support explicit todo2code `create` actions.
6. Make the verification gate honor Docker and every configured completion
   command.
7. Add regression tests, run focused and repository verification, then commit
   only the intended integration scope.

## Risks

- Tightening defaults can leave previously autonomous tickets waiting for an
  explicit executor decision.
- Existing Planfile schemas may drop custom fields during import.
- Docker verification must remain deterministic and non-interactive.

## Acceptance criteria

See [README.md](README.md).

## Validation conclusion

The integration now consumes deterministic communication records, reads
declared `governancePaths` from a target `.governance/manifest.json`, fails
closed when that manifest is malformed, and prevents source patches from
approving or applying themselves. The target's Docker verification declaration
is resolved into every configured container command. A real dry discovery run
produced 12 communication records and no warnings; two actionable source plans
remained after governance and path validation.
