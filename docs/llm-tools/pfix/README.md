# pfix — self-healing Python errors

## Co to jest

LLM-driven auto-fix dla typowych błędów Python: `ImportError`,
`AttributeError`, `TypeError`, `SyntaxError` (rare). Czyta stack trace,
proponuje patch, opcjonalnie aplikuje.

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Plik się nie uruchamia, masz traceback | `pfix run python script.py` |
| Test pyta failuje z ImportError | `pfix fix --error-file pytest.log` |
| CI runner wykrył błąd, chcesz auto-fix | (nie zalecane — Windsurf jest lepszy) |
| Healing-webhook strategy (planowane) | TBD |

## Konfiguracja

### Env vars (per-projekt: `.env`, `backend/.env`, `site/.env`, `dsl/.env`)

```bash
OPENROUTER_API_KEY=sk-or-v1-...
PFIX_MODEL=openrouter/deepseek/deepseek-v4-pro   # default w c2004
PFIX_AUTO_APPLY=true                              # apply bez pytania
PFIX_MAX_ITERATIONS=3                             # max pętli auto-fix
PFIX_TIMEOUT=60                                   # sekundy per iteration
```

### Config plik (opcjonalnie)

`pfix.yaml` w katalogu projektu — można pominąć, env vars wystarczą.

## Komendy

```bash
# Uruchom skrypt z auto-fix gdy błąd
pfix run python backend/app/main.py

# Auto-fix z pliku z errorem (pytest log, traceback)
pfix fix --error-file /tmp/pytest.log --target backend/

# Dry-run — pokaż patch, nie aplikuj
pfix fix --error-file traceback.txt --dry-run

# Verbose
pfix run -v python script.py
```

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/.env` | `PFIX_MODEL` (przez `LLM_MODEL` chain) |
| `@/home/tom/github/maskservice/c2004/backend/.env` | per-package config |
| `@/home/tom/github/maskservice/c2004/site/.env` | per-package config |
| `@/home/tom/github/maskservice/c2004/dsl/.env.example` | per-package config |

**Nieużywane w healing-webhook** (na razie). Propozycja w
`docs/SESSION-2026-05-09-summary.md` sekcja 6 — dodanie strategii
`heal_pfix` w healing-webhook.

## ⚠️ Ostrzeżenie

`PFIX_AUTO_APPLY=true` modyfikuje pliki **bez review**. W c2004 zalecamy:

1. **Default OFF** dla CI runner: `PFIX_AUTO_APPLY=false`
2. **Local development OK**: `PFIX_AUTO_APPLY=true` ale tylko z git clean tree
3. **Healing-webhook (przyszłe)**: zawsze tworzyć ticket, NIE auto-apply

Powód: pfix używa LLM → możliwa halucynacja. Bez review → bug w `main`.

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `pfix: command not found` | `pip install --user pfix` |
| `OPENROUTER_API_KEY not set` | Dodaj do `.env` w katalogu z którego uruchamiasz |
| Patches modyfikują niepoprawnie | `PFIX_AUTO_APPLY=false`, zawsze `--dry-run` first |
| Pętla nieskończona | Zmniejsz `PFIX_MAX_ITERATIONS` (np. do 1) |
| Błędy nie naprawiane | Skomplikowany bug — użyj Windsurf agent zamiast |

## Kiedy NIE używać

- Bugi semantyczne (logika zła) — pfix tylko fix'uje obvious errors
- Refactoring całych plików — użyj `redsl improve` lub Windsurf
- Code review — użyj `vallm validate` (tier-2)

## Linki

- Repo: https://github.com/semcod/pfix
- Wersja: `0.1.72` (PyPI)
