# Ticket 314: Voice and NL control bridge for koru commands and planfile queue

- **ID**: ticket-314
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27
- **Planfile**: KORU-289

## Goal and scope

Implement the `koru voice` and `koru nlp` command dispatcher translating natural language voice and text commands into deterministic koru global controls and planfile queue queries.

Supported intents:
1. **Loop / Global Automation Controls**:
   - Stop / Pause: "zatrzymaj pętlę", "zatrzymaj", "stop", "wyłącz", "wyłącz koru", "pause" -> invokes `koru off` (disables global loop control)
   - Start / Resume: "wznów", "start", "włącz", "włącz koru", "uruchom", "start loop", "resume" -> invokes `koru on` (enables global loop control)
   - Status: "status", "stan", "status pętli", "jaki jest stan", "status koru" -> invokes `koru status` (inspects global loop control)
2. **Queue / Task Queries & Mutations**:
   - Queue Status / Listing: "status kolejki", "pokaż kolejkę", "kolejka", "co w kolejce", "ile zadań" -> queries planfile queue and returns formatted task summary
   - Task Details / Next Task: "pokaż zadania", "lista zadań", "następne zadanie", "co robisz" -> inspects active queue task
   - Task State Transitions: "zamknij zadanie <id>", "zakończ zadanie <id>" -> transitions queue task
3. **Resilience & Determinism**:
   - Levenshtein typo tolerance, Polish phonetic stem matching, case and whitespace normalization.
   - Zero-dependency standard library parser with structured JSON output option (`--json`).

## Acceptance criteria

- [x] AC-01: `src/koru/voice/` provides `VoiceDispatcher` with deterministic intent matching and command translation.
- [x] AC-02: `koru voice` and `koru nlp` subcommands are registered in `src/koru/cli.py` and execute loop and queue actions.
- [x] AC-03: `tests/test_voice_bridge.py` verifies all voice commands, typo tolerance, Polish and English phrases, and CLI invocation.
- [x] AC-04: `project/governance-check.sh` reports `GOV-PASS: passed (0 errors, 0 warnings)`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
