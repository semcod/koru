# Ticket 313: Wake idle queue on admitted work and reset backoff after progress

- **ID**: ticket-313
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-27

## Goal and scope

PLF-062 / semcod/koru#523: c2004 finished three real diagnostic tasks but
increased its idle streak and slept 900 seconds. New tasks did not wake it.
Reset stagnation on successful queue progress and interrupt plain idle sleep
when native Planfile admits machine work in the selected queue. Preserve
provider/failure waits, operator holds and dependency admission.

SESSION_EXECUTION_AUTHORIZATION: user requested continued repairs, tests and
pilots on 2026-09-27. Allocation uses the independently merged HOME allocator
5f21f21 (new-project#411) with adopter admission and layout helpers; the first
attempt saw refs change, and the old adopter allocator refused unrelated dirty
primary state. Foreign files and managed adopter files remain untouched.

## Acceptance criteria

- [ ] AC-01: Successful drained work resets the idle streak; failed cycles retain backoff.
- [ ] AC-02: Eligible queue arrivals wake idle sleep; held/human/missing-dependency work and failed probes do not.
- [ ] AC-03: Unit and native Planfile regression pass; installed runtime pilot wakes without restart after enqueue.

## Boundaries

No change to model permissions, shell-drive completion, hardware, provider
cooldowns or other Koru services. Protected independent Validator owns merge.
