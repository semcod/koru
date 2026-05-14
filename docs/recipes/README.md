# Przepisy koru (recipes) — katalog (plan)

Ten katalog to **dokumentacja i szkice** przyszłych przepisów koru — wersjonowanych
„recept” (np. migracje, spójne zestawy bramek jakości) powiązanych z polityką
YAML i planfile. Docelowo CLI może udostępniać m.in. `koru recipe list` /
`koru recipe apply` (suchy run przed zapisem); na dziś **nic w tym katalogu nie
jest obowiązkowo ładowane przez parser** — to miejsce na propozycje i przykłady.

## Jak zaproponować przepis

1. Dodaj plik YAML (lub rozszerz istniejący szkic) w `docs/recipes/`, z krótkim
   komentarzem na górze: cel, wymagania, ryzyko.
2. Otwórz PR z opisem: **co robi przepis**, dla jakiego typu repozytoriów, czy
   wymaga ręcznej weryfikacji.
3. Jeśli przepis ma wejść do narzędzia jako oficjalna ścieżka, uzgodnij to w
   backlogu (roadmapa: katalog przepisów i polityka w `docs/roadmap-competition.md`).

## Przykłady w repozytorium

- [`python-quality-baseline.yaml`](./python-quality-baseline.yaml),
  [`monorepo-hygiene.yaml`](./monorepo-hygiene.yaml) — szkice placeholderów
  (baseline jakości Pythona oraz higiena monorepo; tylko dokumentacja).
