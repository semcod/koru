# rebuild — Code Evolution Intelligence Engine

## Co to jest

`rebuild` (PyPI: `rebuild>=0.1.34`) to **historical deployment analysis**
+ **code intelligence** — walk git history dzień po dniu, deploy per
commit, test all endpoints, capture screenshots, **analyze code evolution**
żeby znaleźć duplicates, rank quality, generate refactor plans.

W c2004 widoczny jako `rebuild-dash` container w `docker-compose.quality.yml`.

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Walk git history + deploy per commit | `rebuild walk` |
| Restore last green endpoint | `rebuild restore <endpoint>` |
| Quality dashboard (web UI) | `rebuild serve` (port 7821) |
| Refactor plan from history | `rebuild plan --output plan.md` |
| Quality stats per commit | `rebuild stats` |

## Konfiguracja

### Brak osobnego configu

Wszystko CLI flags + reads `pyqual.yaml` jeśli obecny.

### Env vars

| Env var | Cel |
|---|---|
| `REBUILD_DAYS=30` | how many days back to walk |
| `REBUILD_VERBOSE=1` | verbose logs |

## Komendy

```bash
rebuild --version
rebuild --help

# Historical walk
rebuild walk                       # last 30 days, one commit/day
rebuild walk --since 2026-01-01    # explicit start
rebuild walk --endpoints /health,/api/v1   # subset

# Restore
rebuild restore /api/v1/users      # restore last green version of endpoint

# Dashboard (web UI at :7821)
rebuild serve                      # start dashboard
rebuild serve --bind 0.0.0.0:7821  # custom bind

# Refactor planning
rebuild plan                       # generate refactor plan
rebuild plan --based-on duplicates # focus on duplicate elimination
```

## Integracja z koru

Rebuild fits w **healing loop** patterns:

| Plik | Rola |
|---|---|
| `templates/observability/prometheus/rules/app-alerts.yml.template` | `healing_strategy: rebuild_restore` w EndpointDown alerts |
| Healing webhook | invoke `rebuild restore <endpoint>` przy critical alerts |
| `templates/docker-compose.quality.yml.template` | `rebuild-dash` container (port 7821) |

## Reference

- Repo / PyPI: https://pypi.org/project/rebuild/
- Wersja: `rebuild==0.1.34`
- Stats: 634 tests passing, coverage 72%, SUMD: 3722 functions
- Companion: `sumd` (snapshots), `redup` (duplicates), `regix` (regressions)

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `rebuild: command not found` | `pip install --user --upgrade rebuild` |
| Walk wolny | użyj `--days 7` zamiast 30 |
| Dashboard 404 | sprawdź czy `.rebuild/` istnieje (tworzony przy pierwszym walk) |
