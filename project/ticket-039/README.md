# Ticket 039: Harden nested and external Docker build supply chain

- **ID**: ticket-039
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Establish the missing repository ownership boundary required by issue #64
before changing nested Docker build inputs. Assign only Docker-specific paths
under `docker/`, `examples/`, and `services/` to the infrastructure workstream;
keep test-owned Docker fixtures under the existing application boundary.

## Acceptance criteria

- [x] AC-01: The active user explicitly authorized autonomous continuation and
  sequential closure of the remaining tasks on 2026-09-01.
- [x] AC-02: Every currently unowned nested Dockerfile and example Compose
  declaration consumed by Koru has a narrow infrastructure ownership pattern.
- [x] AC-03: Existing application, integration, governance and interface
  ownership remains unchanged and test fixtures remain application-owned.
- [ ] AC-04: Managed governance, Docker Compose and exact-head protected
  publication pass before supply-chain implementation begins.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION` is recorded from the user's request to
continue autonomously and close all remaining tasks in sequence. It grants no
secret access, self-approval, direct merge or unrelated mutation.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
