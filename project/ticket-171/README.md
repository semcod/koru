# Ticket 171: adopt latest wellmanifest standards

- **ID**: ticket-171
- **Owner**: agent
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

Adopt and synchronize current verified Wellmanifest standard packs in `.governance/standard-adoption.json` and `.governance/standard-pack-evidence/*.json`:
- `wellmanifest/new-project` 0.20.32 (`b6ba9c21a65a6a5648ecf904b64c3b75295e136f`)
- `wellmanifest/git-lifecycle` 0.2.0-dev (`2f8ba2ee724fce603ead2c3067c698d3c2ce0e59`)
- `wellmanifest/worktrees` 0.5.3 (`d8e91cfe1fa923bf825fa7a4aa0da1c6e84a2a93`)
- `wellmanifest/merge` 0.1.0-dev (`d514ea17cdd0dda3e3a540779d91ed53951f76b0`)
- `wellmanifest/validation-attestation` 0.1.0-dev (`17017b62374ccf8370d9b50efd3b8f44f66a09e8`)
- `wellmanifest/ticket-lifecycle` 0.1.0-dev (`ad363efa7705919ff613305172bf8115ccf50b15`)
- `wellmanifest/logs` 0.3.0 (`48c284ef7a069055c0bcb6b900147ce5e65f8b43`)

SESSION_EXECUTION_AUTHORIZATION: the user explicitly requested execution, push and merge in this conversation.

## Acceptance criteria

- [x] AC-01: `.governance/standard-adoption.json` updated with latest verified standard pack revisions.
- [x] AC-02: `.governance/standard-pack-evidence/*.json` updated with valid upstream CI receipts and protection receipts.
- [x] AC-03: `standard_pack_check.py`, `standard_pack_projection_check.py`, and `governance_check.py` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
