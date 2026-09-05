# Raport lokalnej publikacji Koru

Zweryfikowano 2026-09-05 przez GitHub API. Instrukcja operatora:
[publication-local-onedev-validator.md](./publication-local-onedev-validator.md).

## Potwierdzone scalone PR

| PR | Zakres | Data scalenia UTC | Commit scalenia |
| --- | --- | --- | --- |
| [#100](https://github.com/semcod/koru/pull/100) | Konsolidacja DSL i registry | 2026-09-02 13:04:32 | `1994ed4df5a6d1f4f3baf77733904a45ccc2e615` |
| [#101](https://github.com/semcod/koru/pull/101) | Skrypt lokalnej publikacji OneDev i Validator | 2026-09-02 19:02:40 | `52e69c9acfdc635384a05fa8a6a8eb9fc58f2a06` |
| [#110](https://github.com/semcod/koru/pull/110) | Deduplikacja odtwarzania zdarzeń DSL | 2026-09-02 21:20:35 | `b6bcaa6fbe96008254f52163635dd5a51a922da6` |

Metadane PR potwierdzają scalenia. Nie stanowią osobnego dowodu czasu wykonania
lokalnych testów ani ich liczby. Pierwotna notatka opisywała próbę dry-run na
PR #110; bez trwałego, powiązanego z HEAD wyniku nie traktujemy jej jako
potwierdzonej walidacji ani jako uprawnienia dla kolejnej publikacji.

## Wymagana kolejność

1. Wydziel materialną zmianę w worktree właściwego ticketu. Nie commituj na `main`.
2. Uruchom zarządzane governance i testy wymagane dla danego zakresu.
3. Dostarcz PR przez `goal -a --delivery-mode pull-request` z właściwym `--ticket`.
4. Odczytaj bieżący HEAD PR bezpośrednio przed zaufaną walidacją. Od tego momentu
   nie pushuj nowych commitów do zatwierdzenia albo jawnej porażki walidacji.
5. Uruchom `scripts/publish-local-onedev-validator.sh` dla tego PR i ticketu,
   aby wykonać lokalne kontrole oraz dispatch Validatora zgodnie z bieżącym profilem.
6. Scalenie wykonuje chroniony Validator po zatwierdzeniu dokładnego HEAD.

Wartość `--ticket` musi odpowiadać badanej zmianie także przy `--dry-run`.
Nie należy używać innego ticketu tylko po to, aby przejść bramkę.

## Co oznaczają błędy z lokalnej próby

- `GOV-AGENT-HOST-001`: gałąź `main` nie jest gałęzią implementacyjnego ticketu.
- `GOV-SCOPE-001` / `GOV-WORKSTREAM-003`: pliki nie należą do zakresu lub workstreamu ticketu.
- `GOV-BASE-002`: baza zmieniła się w zakresie komponentu; potrzebne jest odświeżenie i ponowna walidacja.
- `GOV-BUDGET-001`: zmiana wymaga podziału na mniejsze, zależne zakresy.

Te błędy wymagają uporządkowania pracy, a nie wyłączenia hooka lub testu.
Bieżący katalog `.governance/diagnostics.json` pozostaje źródłem reguł naprawy.

## English summary

GitHub confirms the three merges above. This report does not certify historical
local test counts or timings. Every new publication still needs its own ticket,
current-head checks and protected Validator approval. Use the operator guide
and the repository's current publication profile; never substitute a convenient
ticket ID for the ticket that owns the change.
