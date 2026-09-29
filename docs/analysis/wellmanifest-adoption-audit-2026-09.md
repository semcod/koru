---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "wellmanifest-adoption-audit-2026-09",
  "kind": "analysis",
  "version": 1,
  "title": "Koru: audyt adopcji standardow wellmanifest i mapowania Planfile-GitHub",
  "status": "proposed",
  "owner": "semcod/koru",
  "scope": "repository",
  "created": "2026-09-29",
  "updated": "2026-09-29",
  "review_after": "2026-10-13",
  "source_revision": "8bd8687abd5684b6e8f50b7ff85c8c7215c922be",
  "affected_repositories": [
    "semcod/koru"
  ],
  "evidence": [
    ".governance/standard-adoption.json",
    ".governance/docs.json",
    "https://github.com/semcod/koru/issues/540",
    "https://github.com/semcod/koru/issues/541",
    "https://github.com/semcod/koru/issues/169",
    "https://github.com/semcod/koru/pull/178"
  ]
}
---
# Audyt adopcji standardow wellmanifest (STARTER-605)

Data audytu: 2026-09-29. Zakres: tylko to repozytorium; dokument aktualizuje
obserwacje z audytu 2026-09-15. Porownanie dotyczy HEAD galezi domyslnej
repozytoriow `wellmanifest/*` observowanych przez `git ls-remote` + `VERSION`,
nie jest dowodem, ze kazda zmiana wymaga podbicia pina.

## Deklaracje adopcji vs observowany upstream

Zrodlo deklaracji: `.governance/standard-adoption.json` (mode=enforce,
profile=baseline) oraz `.governance/docs.json` dla wellmanifest/docs.

| Standard | Adopted revision | Adopted version | Upstream HEAD | Upstream VERSION | Status |
|---|---|---|---|---|---|
| wellmanifest/new-project | e2fd653ff801 | 0.20.38 | fa7972da8f6a | 0.20.54 | pin-differs-review-required |
| wellmanifest/git-lifecycle | 2f8ba2ee724f | 0.2.0-dev | 2f8ba2ee724f | 0.2.0-dev | head-match |
| wellmanifest/worktrees | d8e91cfe1fa9 | 0.5.3 | d8e91cfe1fa9 | 0.5.3 | head-match |
| wellmanifest/merge | d514ea17cdd0 | 0.1.0-dev | 7e59cdfe6ecf | 0.1.0-dev | pin-differs-review-required |
| wellmanifest/validation-attestation | 17017b62374c | 0.1.0-dev | 8eb9e2d4eae3 | 0.1.0-dev | pin-differs-review-required |
| wellmanifest/ticket-lifecycle | ad363efa7705 | 0.1.0-dev | 0a5547c1893a | 0.2.0-dev | pin-differs + minor upstream bump |
| wellmanifest/logs | 48c284ef7a06 | 0.3.0 | cd9d9558e09b | 0.5.0 | pin-differs + minor upstream bump |
| wellmanifest/docs | 9fb5fc4d99af | (brak VERSION) | 19efafbeb189 | (brak VERSION) | pin-differs-review-required |

Zmiany wzgledem audytu 2026-09-15:

- new-project: adopcja podbita 0.20.25 -> 0.20.38 (upstream w tym czasie
  przeszedl 0.20.31 -> 0.20.54) — pin nadal odbiega od HEAD.
- git-lifecycle: byl pin-differs, teraz head-match (adopcja do 2f8ba2ee).
- worktrees: head-match utrzymany (0.5.3).
- ticket-lifecycle: upstream podbil version 0.1.0-dev -> 0.2.0-dev —
  kandydat na osobny ticket adopcji (managed adopter).
- logs: upstream 0.3.0 -> 0.5.0 — kandydat na osobny ticket adopcji.
- merge, validation-attestation, docs: pin-differs przy tym samym numerze
  wersji — przeglad tresciowych roznic przed ewentualnym podbiciem.

## Planfile ID <-> GitHub issue: mapowanie i deduplikacja

- Kazdy rekord Planfile (`PLF-*`, `STARTER-*`) ma `source.context.dedupe_key`
  postaci `code2llm:smell:<kind>:<path>` albo jawny klucz w tresci issue
  (`planfile:deduplication-key=semcod/koru:<digest>:<TICKET-ID>`).
- Issue na GitHub niesie w tresci `planfile_id: semcod/koru:<digest>:<TICKET-ID>`
  — mapowanie lokalne->zdalne jest deterministyczne i odwracalne.
- Sprawdzono aparentny duplikat: issue #540 i #541 maja identyczny tytul
  "God Function: main", ale rozne planfile_id (PLF-037 w
  `packages/uri2koru`, PLF-038 w `packages/nlp2koru`) — to rozne smelly;
  deduplikacja dziala poprawnie per klucz, nie per tytul.
- Rekordy lokalne nie przechowuja numeru issue (pole `sync` puste);
  powiazanie dziala w kierunku issue->planfile_id. Brak dowodu na
  zdublowane issue dla tego samego klucza w observowanej probie.

## Deklarowane vs egzekwowane (protected CI)

- Lokalna bramka `./project/governance-check.sh` przechodzi (GOV-PASS) na tym
  ticketcie; CI "governance / enforce" + "standard packs / conformance"
  przechodzi na scalonych PR-ach #618-#622.
- Publicacja wymaga lokalnego Validatora (exact-head): observowane merge'y
  #600-#622 przez `validator-local-reconcile@semcod-koru` — timer
  OneDev->Validator dziala; cykliczne `retry_cooldown`/`onedev_pending`
  sa normalne przy przesuwajacym sie main.

## Niezrealizowane / przekazane

- Podbicie pinow (ticket-lifecycle 0.2.0-dev, logs 0.5.0, new-project
  0.20.54) — osobne bounded tickety przez managed adopter; poza zakresem
  tego audytu ("planning, not authorization to modify").
- STARTER-606 (walidacja dokumentow w sciezce generatora) — osobny ticket.
- PLF-060 / PLF-062 — dotycza wdrozonego runtime c2004; poza zakresem repo.
