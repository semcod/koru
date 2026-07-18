# Pointer: ocena Koru ↔ Subactor (2026-07-18)

Pełny raport (Part A: subactor ask / publikacje domen; Part B: checklist Werdykt vs kod Koru):

**`/home/tom/github/subactor/docs/architecture/koru-subactor-autonomy-assessment-2026-07-18.md`**

## Skrót (5 zdań)

- Subactor ask: pełny apply = `--execute --apply --yes`; po edycji `step-catalog.json` → `docker compose restart hr-control` w `platform/`.
- Logo/www/docs-stage: apply na origin OK (200); logo używa `/logo.subactor.com`; docs.prod celowo bez apply.
- Koru queue: worktree + dirty refuse + manifest drift + retry(1) — **częściowo** spełnia Werdykt; brak trwałego manifestu per run i niedokończony `promotion_mode=commit`.
- Most `development_defect` Subactor→Koru jest w repo; Koru nie powinien mutować Plesk/DNS.
- P0 wspólne: ADR-005 Accept, persist manifest, regresja stale step-catalog, E2E bridge test.
