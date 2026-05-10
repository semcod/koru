# costs — Zero-config AI cost calculator per commit/model

## Co to jest

`costs` (PyPI: `costs>=0.1.50`) to **per-commit AI cost tracker** używający
liteLLM do estymacji tokenów. Generuje:

- **Cost badges** w README.md (`![AI Cost](https://img.shields.io/badge/AI%20Cost-$0.45-orange)`)
- **Cost reports** z visualizations (per-model, per-period)
- **Per-commit estimaty** dla planowania budżetu

W koru widzisz badge w `README.md`:
`![AI Cost](https://img.shields.io/badge/AI%20Cost-$0.45-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-2.0h-blue)`

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Init w nowym repo | `costs init` |
| Update badge w README.md | `costs auto-badge` (po commit) lub `costs badge` |
| Pełna analiza historii git | `costs analyze` |
| Generuj report z visualizations | `costs report --format html` |
| Estimate kosztu dla diff | `costs estimate <commit-sha>` |
| Stats całego repo | `costs stats` |

## Konfiguracja

### Brak osobnego configu — auto-detect

`costs` automatycznie:

- czyta git history dla obliczeń per-commit
- używa liteLLM dla token counting (zero-config — działa dla 100+ modeli)
- detect-uje model z env (`LLM_MODEL`, `OPENROUTER_MODEL`) lub commit metadata

### Env vars (opcjonalne)

| Env var | Cel |
|---|---|
| `LLM_MODEL` | default model dla estymacji (np. `openrouter/qwen/qwen3-coder-next`) |
| `COSTS_HOURLY_RATE` | stawka human dev (default: 100 USD/h) |
| `COSTS_DEDUP_MINUTES` | dedup window dla commits (default: 30) |

### `pyproject.toml` integration (auto-badge)

```toml
[tool.costs]
model = "openrouter/qwen/qwen3-coder-next"
hourly_rate = 100
dedup_minutes = 30
badges = ["ai_cost", "human_time", "model"]
```

`costs auto-badge` używa tej konfiguracji.

## Komendy

```bash
costs --version                   # 0.1.50+
costs --help

# Setup
costs init                        # initialize w current repo

# Analyze + reports
costs analyze                     # full git history analysis
costs analyze --since 2026-04-01  # tylko po dacie
costs analyze --model gpt-4o      # explicit model override

costs report                      # text report
costs report --format html -o costs.html
costs report --format json -o costs.json

# Single commit estimate
costs estimate                    # current diff (uncommitted)
costs estimate HEAD~5..HEAD       # range
costs estimate <sha>              # single commit

# Stats
costs stats                       # repo-wide stats
costs stats --period weekly       # weekly breakdown

# Badges (Shields.io style)
costs badge                       # generate AI Cost badge → update README.md
costs auto-badge                  # use pyproject.toml [tool.costs] config
```

## Integracja z koru

| Plik | Rola |
|---|---|
| `README.md` (badge sekcja) | `![AI Cost](...)` + `![Human Time](...)` + `![Model](...)` badges |
| `pyproject.toml` (opcjonalnie `[tool.costs]`) | Konfiguracja `auto-badge` |
| Workflow CI | `costs auto-badge && git add README.md` jako post-merge step |

W koru wszystkie semcod/* projekty mają costs badges w README.md (widać
zwłaszcza w `metrun/README.md`, `op3/README.md`, `mdflow/README.md` itd.):

```markdown
![PyPI](https://img.shields.io/badge/pypi-costs-blue)
![Version](https://img.shields.io/badge/version-0.1.34-blue)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$2.40-orange)
![Human Time](https://img.shields.io/badge/Human%20Time-5.6h-blue)
![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)
```

## Reference deployment (c2004)

c2004 README.md ma analogiczne badges. `costs` jest standardem w semcod/*
ekosystemie:

| Repo | Badge widoczny |
|---|---|
| `koru/README.md` | `$0.45` (3 commits) |
| `op3/README.md` | `$2.40` (16 commits) |
| `metrun/README.md` | `$1.97` (8.7h human) |
| `mdflow/README.md` | obecny |
| `costs/README.md` | self-tracking ($0.81 / 6.2h) |
| c2004 | obecny |

## Companion tools

- **`goal`** — auto-add costs badge przy każdym `goal commit` (jeśli
  `[tool.costs] auto_badge=true` w pyproject)
- **`llx`** / **`redsl`** / **`pfix`** — wszystkie używają liteLLM, costs
  rejestruje ich token usage przez liteLLM logging
- **`nfo`** — structured logs z token counts (compatible z costs analyze)

## Workflow: commit → cost tracking → badge

```bash
# 1. Pracuj normalnie:
git add -A
git commit -m "..."

# 2. Update cost tracking:
costs analyze            # analizuje wszystkie nowe commits
costs auto-badge         # update badge w README.md

# 3. Commit badge update:
git add README.md
git commit -m "chore(badge): update AI cost tracking"

# Lub auto-flow z goal:
goal -a                  # goal automatically calls costs auto-badge
```

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `costs: command not found` | `pip install --user --upgrade costs` |
| `liteLLM not found` | `pip install litellm` (auto-installed jako dep) |
| Badge ma `$0.00` | sprawdź czy commit messages zawierają model info, albo set `LLM_MODEL` env |
| Bardzo wolny `costs analyze` | użyj `--since <date>` lub `--max-commits 50` |
| Badge nie aktualizuje README | sprawdź czy README.md ma marker `<!-- costs:badge -->` lub że badge URL jest w pierwszych 30 liniach |

## Linki

- Repo / PyPI: https://pypi.org/project/costs/
- Wersja (2026-05-10): `costs==0.1.50`
- Reference: badges w README.md wszystkich semcod/* projektów
- Companion: `goal` (auto-update przy commit), `llx` (token tracking via liteLLM)
