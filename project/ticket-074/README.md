# Ticket 074: Compress Order 30 NLP intent translation

- **ID**: ticket-074
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Replace repeated natural-language action branches and LLM plan construction
with compact, ordered specifications in canonical `nlp2koru`. Preserve public
symbols, heuristic precedence, central SubLLM routes and the one-release
`nlp2coru` compatibility behavior while reducing Order 30 production lines.

The user's 2026-09-02 instruction to continue is
`SESSION_EXECUTION_AUTHORIZATION` for this bounded implementation and its
protected publication.

## Acceptance criteria

- [x] AC-01: Session execution authorization is recorded for this bounded
      Order 30 slice.
- [x] AC-02: Ordered immutable rules preserve heuristic action and install
      precedence across English, Polish and fallback prompts.
- [x] AC-03: Canonical and legacy LLM routes share plan construction while
      retaining their exact route names and safe heuristic fallback.
- [x] AC-04: A focused behavioral matrix covers actions, lane mentions, DSL
      rendering, invalid LLM payloads and both central routes.
- [x] AC-05: Focused suites, Ruff, compile, governance, overlap, Docker Compose
      and diff gates pass before protected publication.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
