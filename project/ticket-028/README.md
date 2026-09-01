# Ticket 028: Adopt resumable conflict-safe merge streaming

- **ID**: ticket-028
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-09-01

## Goal and scope

Make future Koru delivery fast to stream, easy to isolate and resistant to
conflicts without weakening exact-head merge authorization. Adopt the latest
final immutable `wellmanifest/new-project` release, `0.19.19` at verified
commit `43999c793a86084b4c3198fe07be350105db59ec`, using system Goal 2.1.300.

The adoption installs managed ticket allocation, work-continuity checkpoints,
canonical durable worktree planning, active overlap detection, terminal
workspace cleanup and branch-lifecycle validation. Koru's target overlay will
add `packages/**` application ownership required by issue #37 and make
`.gitignore` an explicit governance path so the four managed host files can be
tracked. Required package metadata, agent-host hooks and immutable Docker
configuration are part of the same reviewed atomic adoption.

The role-based standard-pack seed remains in `audit` until every HOME pack has
its own immutable projection provenance and protected S3/S4 receipt. The audit
therefore reports seven explicit missing pack adoptions instead of converting
workflow URLs or empty artifact lists into unsupported enforcement claims.

Future delivery uses one canonical worktree under
`<workspace>/.worktrees/<repo>--ticket-NNN--<slug>`, never a system temporary
directory or parallel ad-hoc worktree root. Implementation commits may stream
to a draft PR without waiting for superseded checks. Before publication the
branch refreshes from `main`, runs local gates once, freezes one final HEAD and
dispatches `koru ci publish --watch --merge`; no push is allowed after freeze.
The protected controller merges and deletes the branch, and the new lifecycle
contract eliminates repository-authored closure PRs.

GitHub receives a `main` ruleset that rejects direct human pushes, force pushes
and deletion, requires pull requests and the protected local-verification
status, and permits merge only through the trusted Validator boundary. A merge
queue is deliberately deferred because it would replace the reviewed PR HEAD
with a merge-group SHA that the present exact-head validator does not bind.

The implementation already present before this ticket remains untouched.
Ticket 027 is terminal: its protected repair PR #60 merged as `4d37bc6a`, and
its legacy closure PR #61 merged as `d4c3075f`. Its worktrees and recovery
stashes are outside this ticket's write scope.

## Acceptance criteria

- [x] AC-01: The active user explicitly requested continuation, implementation
  and deployment of this scope on 2026-09-01.
- [x] AC-02: Goal adopts published `new-project` 0.19.19 at exact SHA
  `43999c793a86084b4c3198fe07be350105db59ec`; its post-write check reports
  up-to-date and the managed lock matches every managed target.
- [x] AC-03: The approved intent migrates to intent/v3 with the atomic standard
  adoption binding before Goal changes implementation paths; no managed payload
  is hidden as an ordinary local rewrite.
- [x] AC-04: The target manifest assigns `packages/**` to application, allows
  up to four disjoint tickets per workstream and preserves Koru's explicit
  Python/Docker requirements.
- [x] AC-05: Canonical worktree planning, overlap guard, remote-aware ticket
  allocation and work-continuity capture/verify pass; `/tmp`, ad-hoc parallel
  roots and duplicate clones are rejected for publishable ticket work.
- [x] AC-06: Package metadata, host hook activation and Docker image contracts
  satisfy all new deterministic governance checks without disabling a stack or
  suppressing a finding.
- [ ] AC-07: An active GitHub `main` ruleset blocks a direct human push and
  requires PR/check/review flow while the trusted Validator App can still merge
  the frozen exact HEAD; merged topic branches are automatically deleted.
- [ ] AC-08: The streaming protocol is exercised on this ticket: draft PR
  receives intermediate commits, one final refreshed HEAD is frozen, no
  self-binding closure commit is created, and protected publication completes
  within the five-minute Validator SLO.
- [ ] AC-09: Governance, worktree, branch-lifecycle, Python and Docker/Compose
  checks pass; the standard-pack audit records its seven unproven HOME-pack
  requirements without false enforcement; issue #41 closes only after
  protected merge and issue #37 becomes unblocked without being implemented
  here.

## Non-goals

- Revert, rewrite or otherwise alter commits already present on `main`.
- Merge or discard the isolated ticket-027 validation-repair changes.
- Route nlp2koru/nlp2coru through SubLLM; that remains issue #37.
- Add a second merge daemon or bypass `subactor/validator-agent`.
- Enable GitHub merge queue before it binds the validator's reviewed subject.
- Use `/tmp` for any linked worktree or durable work checkpoint.
- Claim S3/S4 conformance for a HOME pack without its own protected receipt and
  projection provenance.
- Harden nested or externally fetched Docker build dependencies; the bounded
  root Docker/Compose contract is enforced here and deeper supply-chain
  hardening remains a separate ticket.

## Publication plan

1. Record terminal ticket-027 evidence and session execution authorization,
   then move this ticket to `IN_PROGRESS / EDIT` in its canonical worktree.
2. Migrate the approved intent to v3/L with the exact atomic-adoption binding,
   then apply Goal and only the deterministic target-specific remediations.
3. Open a draft PR early and stream reviewable commits without waiting for
   superseded remote checks.
4. Refresh from `main`, run final gates, mark ready and freeze a single HEAD.
5. Activate/verify the ruleset and dispatch protected Validator publication;
   do not create a separate governance closure PR.

## Participants

- Human participant: the active user requested future merge-streaming and
  conflict-prevention optimization on 2026-09-01; identity remains unresolved
  and no `user-*` file was created.
- Agent participant: [ai-codex.md](ai-codex.md)
