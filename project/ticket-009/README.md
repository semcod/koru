# Ticket 009: Route Koru LLM work through Cursor Grok 4.6 xhigh

- **ID**: ticket-009
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-16
- **Work classification**: `SERVICE / application`

## Goal and scope

Replace Koru's OpenRouter planning path and OpenAI-compatible queue executor
with one fail-closed SubLLM route executed by the Cursor Python SDK. Both
planning and patch-producing queue calls must use Cursor `grok-4.6` with
`effort=xhigh` and `fast=false`.

Remove Koru-imposed completion-token, context-character, file-count and
monetary guards from requests sent to the LLM. Keep provider context/rate
limits and operational safety controls such as timeouts, bounded retries,
iteration limits, patch policy, verification, isolation and secret exclusion.

Audit the existing scan → ticket → context → proposal → verification →
promotion flow and compare new Grok evidence with historical OpenRouter
artifacts without issuing any new request to the prohibited Qwen or GPT-4o
models.

## Acceptance criteria

- [x] AC-01: The user approved an isolated current-main worktree and the exact
  Cursor `grok-4.6` xhigh mapping in this session.
- [x] AC-02: Planning and queue execution resolve only
  `koru-agent/{planning-assistant,queue-executor}` through SubLLM and fail
  closed without a valid Cursor credential.
- [x] AC-03: Runtime defaults contain no Qwen3 Coder Next or GPT-4o Mini
  planning/executor fallback.
- [x] AC-04: Koru does not impose an LLM monetary budget, output-token cap,
  32k context cap or 12-file context cap.
- [x] AC-05: Unit and integration tests prove model parameters, credential
  redaction, non-mutating planning, patch output handling and retained
  operational safety limits.
- [x] AC-06: An evidence report distinguishes deterministic safeguards from
  publication gaps and compares new Grok results with historical artifacts.

## Risk boundary

This ticket owns runtime source and tests only. Dependency manifests,
lockfiles, release metadata and publication belong to a subsequent integration
ticket. The Cursor SDK is optional until that ticket lands; missing transport
packages fail closed with an actionable error.

## Session authorization

The user explicitly approved the isolated worktree and exact Grok xhigh
strategy on 2026-08-16. This bounded scope proceeds directly to `EDIT`; no
human-owned `user-*.md` file is synthesized.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-gpt-5.6-sol.md](ai-gpt-5.6-sol.md)
