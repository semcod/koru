# Pointer: ocena Koru ↔ Subactor (2026-07-18)

Pełny raport (Part A: subactor ask / publikacje domen; Part B: checklist Werdykt vs kod Koru):

**`/home/tom/github/subactor/docs/architecture/koru-subactor-autonomy-assessment-2026-07-18.md`**

## Skrót (5 zdań)

- Subactor ask: pełny apply = `--execute --apply --yes`; po edycji `step-catalog.json` → `docker compose restart hr-control` w `platform/`.
- Logo/www/docs-stage: apply na origin OK (200); logo używa `/logo.subactor.com`; docs.prod celowo bez apply.
- **P0 done (2026-07-18, `5fea503d`):** ADR-005 Accepted, persist manifest per run, `promotion_mode=commit` on clean main, E2E bridge test.
- **P1 template:** [`docs/subactor-development-repair-template.md`](../subactor-development-repair-template.md) — `patch_mode`, `promotion_mode=branch`, worktree, `max_patch_attempts=2`, local verify.
- Most `development_defect` Subactor→Koru jest w repo; Koru nie powinien mutować Plesk/DNS.
