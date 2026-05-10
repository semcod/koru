# redup — code duplication detection

## Co to jest

AST-hash based scanner duplikatów kodu. **W 100% LLM-free**. Wykrywa
copy-paste między modułami, sugeruje refaktory.

W c2004 cenny dla 50+ `connect-*` mikroserwisów które często mają podobne
helpers, validators, query builders.

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Audit przed dużym refaktorem | `redup scan .` |
| Per-katalog quick check | `redup scan backend/app` |
| Compare dwa scany w czasie | `redup compare-scans old.json new.json` |
| Strict gate w CI | `redup check . --threshold 0.85 --fail` |
| MCP tool dla Windsurf | `python3 -m redup.mcp_server` |

## Konfiguracja

### Brak osobnego configu

Wszystko przez CLI flags:
- `--threshold` — similarity threshold (0.85 = "high similarity")
- `--min-lines` — minimum bloku duplikatu (default 3)
- `--extensions` — `.py`, `.js`, `.ts`, `.jsx`, `.tsx`

### Env vars

```bash
REDUP_ROOT=/home/tom/github/maskservice/c2004    # dla MCP server
```

## Komendy

```bash
# Quick scan
redup scan .

# Format output
redup scan backend/app --format json --output redup-report.json

# Konkretny threshold
redup scan . --threshold 0.90 --min-lines 5

# Compare po refactorze
redup compare-scans before.json after.json

# Strict CI gate
redup check . --threshold 0.85 --max-duplicates 50 --fail

# MCP server (dla Windsurf)
python3 -m redup.mcp_server
```

## Output (przykład z c2004)

```
🔍 Scanning: backend/app
📁 Extensions: .py
📏 Min lines: 3
🎯 Min similarity: 0.85

Duplicate finding completed in 175.3ms
📊 Scanned 80 files (11727 lines, 934ms)
Found 22 duplicate groups (58 fragments, 267 lines recoverable)
```

→ 22 grupy = potencjalny win na refaktor (267 linii do wyciągnięcia
do `packages/backend-shared-py/`).

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/redup.toml` | Konfiguracja + `[exclude]` patterns |
| `@/home/tom/github/maskservice/c2004/scripts/redup-run.sh` | Wrapper — CLI lub fallback do `/home/tom/github/semcod/redup/src` |
| `@/home/tom/github/maskservice/c2004/scripts/redup-check.sh` | Budget gate z post-scan filter (Python) |
| `@/home/tom/github/maskservice/c2004/scripts/redup-precommit.sh` | Advisory pre-commit (opt-in `REDUP_STRICT=true`) |
| `@/home/tom/github/maskservice/c2004/.pre-commit-config.yaml:74-85` | Hook `redup` (advisory) |
| `@/home/tom/github/maskservice/c2004/Taskfile.yml` | `task quality:redup`, `:check`, `:report` |
| `@/home/tom/github/maskservice/c2004/redsl.yaml:20` | `use_redup: true` w stage `perceive` |
| `@/home/tom/github/maskservice/c2004/monitoring/healing-webhook/app.py:454-547` | Strategy `heal_redup_check` + 3 metryki Prometheus |
| `@/home/tom/github/maskservice/c2004/monitoring/healing-webhook/Dockerfile:23` | `redup>=0.4.15` w obrazie |
| `@/home/tom/github/maskservice/c2004/.windsurf/mcp_config.example.json` | MCP server entry dla Windsurf |

## Healing-webhook strategy `redup_check`

Wywoływana przez Alertmanager webhook gdy `healing_strategy=redup_check`:

```bash
curl -s -X POST http://localhost:8810/alertmanager -H "Content-Type: application/json" -d '{
  "alerts": [{
    "status": "firing",
    "labels": {
      "alertname": "DuplicationCheck",
      "severity": "warning",
      "component": "monorepo",
      "healing_strategy": "redup_check"
    },
    "annotations": {"summary": "Periodic duplicate-budget check"}
  }]
}'
```

Outcomes:

- `within_budget` — log + metric only
- `budget_breached` — record action; przy `severity≥error` healing-webhook
  tworzy ticket z label `redup-detected`
- `skipped` — `redup` lub `redup-check.sh` brak w obrazie

## Metryki Prometheus

```
c2004_redup_groups           # liczba grup po filtrze
c2004_redup_saved_lines      # sumaryczne linie do odzyskania
c2004_redup_budget_breach    # 1 jeśli budżet przekroczony, 0 inaczej
```

Ustawione przy każdym uruchomieniu `_run_redup_check()`. Można scrape'ować
przez Prometheus / wizualizować w Grafanie obok pozostałych quality metrics.

## MCP integration

Windsurf agent z MCP może wywołać 8 tools:

```
analyze_project, check_project, compare_projects, compare_scans,
find_duplicates, info, project_info, suggest_refactoring
```

Ostatni (`suggest_refactoring`) używa heurystyk — nie LLM — do propozycji
gdzie przenieść duplikat (np. do `packages/shared/`).

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `redup: command not found` | `pip install --user redup` |
| Bardzo wolne na monorepo | `--extensions .py` (skip .js/.ts), lub `--exclude "node_modules/**"` |
| Zbyt wiele false positives | `--threshold 0.95` (strict), lub `--min-lines 10` |
| MCP server: "No module named redup.mcp" | Reinstall: `pip install --user --upgrade redup` |

## Linki

- Repo: https://github.com/semcod/redup
- Wersja: `0.4.15` (PyPI)
- W c2004: 22 duplicate groups w `backend/app` (audit z 2026-05-10)
