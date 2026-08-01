# Ticket 001 — governance-aware todo2code integration

- Status: DONE
- Workflow state: DONE
- Owner: unresolved:human
- Agent: agent:codex
- Approval: user approved the proposed remediation plan with `tak`

## Scope

Make Koru consume todo2code communication evidence, protect governance-owned
files, remove unapproved self-application, route executable patches through the
manifest transaction, and verify using the target project's declared runtime.

## Acceptance criteria

- todo2code communication analysis is enabled by default.
- Autonomous code changes cannot target governance or participant files.
- A todo2code patch cannot bypass Koru's manifest/authorization transaction.
- Human tickets are not silently promoted to autonomous LLM execution.
- File-creation plans supported by todo2code remain actionable.
- Verification honors Docker-first projects and all configured completion gates.
- Focused tests and the relevant repository verification pass.

## Validation status

- Docker lint and the focused integration suite pass.
- A real deterministic todo2code run succeeds with project communication
  enabled and target governance loaded from `project/`.
- Full-suite Docker validation still exposes unrelated socket timeout and
  runtime-UID assumptions outside the todo2code integration.

## Participants

- Human owner: `unresolved:human` (no agent-authored `user-*` file)
- Agent: [ai-codex.md](ai-codex.md)
- Raw command log: [ai-codex-logs.txt](ai-codex-logs.txt)
- Changes: [changelog.md](changelog.md)
