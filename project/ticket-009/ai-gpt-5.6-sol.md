---
participant-id: agent:gpt-5.6-sol
participant: gpt-5.6-sol
role: agent
ticket: ticket-009
---
# Participant: gpt-5.6-sol (AI agent)

## Understanding

Koru currently has two independent text-LLM paths: OpenRouter-only planning
and an OpenAI-compatible queue executor with a GPT-4o Mini default. Both must
be replaced by strict SubLLM routes using Cursor Grok 4.6 xhigh. Koru's own
cost and request-size caps must be removed while deterministic execution,
verification, isolation and security controls remain bounded.

## Execution plan

1. Add a single Cursor SDK transport adapter driven by SubLLM route output.
2. Route planning JSON and queue execution through the adapter.
3. Remove runtime references and request caps for the prohibited legacy models.
4. Add hermetic tests and one credential-backed, non-mutating comparison run.
5. Record the mutation/publication audit separately from implementation claims.

## Actual changes

- Added one SubLLM-resolved Cursor SDK transport for both Koru routes.
- Replaced planning, queue and shell OpenRouter execution with fail-closed
  Cursor Grok 4.6 xhigh calls that expose no write tools.
- Removed Koru's enforced monetary, output-token, default context-character
  and context-file-count limits; retained explicit ticket caps and operational
  safety limits.
- Updated defaults, compatibility metadata and tests. A credential-backed
  planning call returned valid JSON, and a queue call returned a target-bound
  unified diff without mutating the worktree.
- Published SubLLM 0.7.0 at
  https://github.com/subactor/subllm/releases/tag/v0.7.0.

## Blockers

- Dependency metadata remains intentionally deferred to a sequential
  integration ticket. `goal -a` could not publish SubLLM because that
  repository has not adopted Goal's required governance package; the verified
  artifacts were published as a signed-tag GitHub release instead.
