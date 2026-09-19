# Ticket 174: Reject unusable Planfile queue executables

- **ID**: ticket-174
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-19

## Goal and scope

Fix STARTER-618: a discovered Planfile executable that fails its version probe
must not shadow a working queue executable. The NVIDIA incident selected a
sibling virtual environment whose launcher raised ModuleNotFoundError.

SESSION_EXECUTION_AUTHORIZATION: user requested analysis, repair and execution
in this conversation. Scope is the queue capability probe and its regressions;
ticket-172 retains ownership of standard adoption.

## Acceptance criteria

- [x] AC-01: Failed, timed-out and unlaunchable discovered candidates are rejected.
- [x] AC-02: A broken sibling launcher falls through to a working project launcher.
- [x] AC-03: Existing successful legacy versionless probes remain compatible;
  queue regression tests and governance pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Validation

Queue regressions: 124 passed and 4 subtests passed. The new regression failed
before the fix and passed after it. Ruff and the managed governance gate passed;
governance reported zero errors and zero warnings. Publication is pending
independent OneDev and Validator verification of the committed PR head.
