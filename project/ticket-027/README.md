# Ticket 027: Work commit notify and LLM provenance registry

- **ID**: ticket-027
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-01

## Goal and scope

1. Desktop notification (`notify-send`) after Koru planfile/work commits with
   project URL, provider, model and ticket id.
2. Surface LLM provenance on `koru work next` and in execution-plan signals.
3. Move hardcoded task-profile ordering into `task_profiles.yaml` registry.

## Acceptance criteria

- [x] AC-01: `_commit_planfile_sync` triggers desktop notify with LLM context.
- [x] AC-02: `koru work next` prints planning provider/model and project URL.
- [x] AC-03: `profile_order` and `fallback_profile` live in task_profiles.yaml.
- [ ] AC-04: Protected publication via validator-agent after review.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-cursor-auto.md](ai-cursor-auto.md)
