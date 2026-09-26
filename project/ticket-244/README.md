# Ticket 244: decompose god module context by extracting rules and sprint managers

- **ID**: ticket-244
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-26

## Goal and scope

Decompose the oversized `src/koru/context.py` (957 lines) into cohesive modules:
1. `src/koru/context_rules.py`: LLM brief instruction and self-service command builders (`_build_instructions`, `_build_setup_instructions`, `_build_policy_rules`, `_build_ticket_rules`, `_build_shared_rules`, `_build_self_service`).
2. `src/koru/context_sprint.py`: Sprint data loading, mtime/size caching, and blocking/bug ticket auto-promotion (`_load_sprint_data`, `_fast_yaml_load`, `_find_blocking_tickets`, `_promote_blocking_to_critical`, `_promote_bug_priority`, `_write_sprint_data`, `_auto_promote_blocking_tickets`).
3. `src/koru/context.py`: Core facade and context synthesis (`build_context`, `_assemble_context`, ticket queries, git probe) with explicit re-exports of all extracted symbols to guarantee 100% backward compatibility.

## Acceptance criteria

- [x] AC-01: Extract instruction and self-service builders to `src/koru/context_rules.py`.
- [x] AC-02: Extract sprint cache and auto-promotion to `src/koru/context_sprint.py`.
- [x] AC-03: `src/koru/context.py` re-exports all extracted symbols with `# noqa: F401`.
- [x] AC-04: All existing tests in `tests/test_context.py` pass without regression.
- [x] AC-05: Unit tests in `tests/test_context_rules.py` and `tests/test_context_sprint.py` verify extracted functionality.
- [x] AC-06: `./project/governance-check.sh` passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
