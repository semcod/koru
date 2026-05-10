# vallm — patch validation (LLM-aware)

## Co to jest

Walidator wygenerowanego kodu w 2 trybach:

- **Tier 1 (`check`)** — szybki AST + import + complexity check (~50ms/plik). **LLM-free.**
- **Tier 2 (`validate`)** — pełna pipeline + LLM-as-judge (~3s/plik). **Płatne.**

W c2004 standardowo używamy **tier-1**; tier-2 tylko świadomie i rzadko.

## Kiedy używać

| Scenariusz | Komenda | Tier |
|---|---|---|
| Pre-flight syntax po LLM patch | `vallm check --file foo.py` | 1 (LLM-free) |
| Auto-enrichment ticketu w healing-webhook | (auto, w `app.py`) | 1 (LLM-free) |
| Manual review patcha przed mergem | `vallm validate --file foo.py` | 2 (LLM) |
| CI gate — ostatnia linia obrony | `vallm check --file <changed>` w hooku | 1 |

## Konfiguracja

### Env vars (opcjonalne)

```bash
OPENROUTER_API_KEY=sk-or-v1-...       # tylko dla tier-2
LLM_MODEL=openrouter/deepseek/deepseek-v4-pro   # dla tier-2 LLM-as-judge
```

### Config plik

Brak — vallm auto-detectuje język i używa AST tooling per language.

## Komendy

```bash
# Tier-1 syntax check (LLM-free)
vallm check --file backend/app/main.py

# Tier-1 z JSON output (machine-readable)
vallm check --file backend/app/main.py --output json

# Tier-2 LLM-as-judge (płatne)
vallm validate --file backend/app/main.py --output json

# Z konkretnym modelem
vallm validate --file foo.py --model openrouter/deepseek/deepseek-v4-pro
```

## Output

```json
{
  "score": 1.0,
  "tier": "check",
  "ok": true,
  "checks": {
    "syntax": "PASS",
    "imports": "PASS",
    "complexity": {"value": 8, "max": 15, "ok": true}
  }
}
```

Score 0.0-1.0:
- `1.0` — wszystkie checki przeszły
- `0.5-0.9` — drobne ostrzeżenia
- `<0.5` — błędy blokujące

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/monitoring/healing-webhook/app.py:267-329` | Helpery `_run_vallm_check`, `_run_vallm_validate` |
| `@/home/tom/github/maskservice/c2004/monitoring/healing-webhook/app.py:332-360` | Auto-enrichment ticketów o sekcję `🔍 vallm pre-flight` |
| `@/home/tom/github/maskservice/c2004/monitoring/healing-webhook/Dockerfile:22` | Pip install |
| Prometheus metrics | `c2004_vallm_score{path,tier}`, `c2004_vallm_runs_total{tier,outcome}` |

## ⚠️ Ważne ostrzeżenie

**Tier-1 NIE łapie bugów semantycznych.** Empirycznie zademonstrowane
2026-05-10 (patrz `docs/SESSION-2026-05-09-summary.md` sekcja 5b):

```python
# DeepSeek V4 Flash wygenerował:
result = result.get(type_name, 0) + 1   # BUG semantyczny

# vallm tier-1: PASS (syntax OK)
# ruff: PASS (lint OK)
# Runtime: CRASH
```

→ **Zawsze dodawaj regression test do każdego ticketa**, nie polegaj
tylko na vallm tier-1 jako safety net.

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `vallm: command not found` | `pip install --user vallm` (wymaga Python 3.12+) |
| `SyntaxError: f"{x[]}"` przy starcie | Vallm wymaga Python 3.12+ — uaktualnij interpreter |
| Tier-1 daje błąd dla JS/TS | Vallm głównie Python; dla JS użyj `eslint` |
| Tier-2 timeout | Zwiększ `--timeout 120` |

## Linki

- Repo: https://github.com/semcod/vallm (lokalnie: `/home/tom/github/semcod/vallm`)
- Wersja: `0.1.71` (editable)
- Healing-webhook integration: 2026-05-09
