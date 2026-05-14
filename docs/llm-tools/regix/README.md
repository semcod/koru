# regix — git-native regression detection

## Co to jest

Wykrywanie regresji metryk kodu (CC, MI, coverage, length, docstring, +13)
między dwoma git refs lub working tree a HEAD. **W 100% LLM-free.**

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Pre-commit gate (auto) | (hook w `.pre-commit-config.yaml`) |
| Working tree vs HEAD | `regix compare HEAD --local` lub `task quality:regix:local` |
| Branch vs main | `regix compare main HEAD` |
| Historical trends | `regix history --commits 10` |
| Strict CI gate | `regix compare HEAD~1 HEAD --fail-on error` |

## Konfiguracja

### `@/home/tom/github/maskservice/c2004/regix.yaml`

```yaml
backends: [lizard, radon, coverage, vallm]   # bez LLM

metrics:
  cc_max: 15                # cyclomatic complexity max
  mi_min: 20                # maintainability index min
  coverage_min: 50          # coverage % min
  length_max: 100           # function length lines max
  docstring_required: false

deltas:
  warn: 2                   # ostrzeżenie przy zmianie ≥2
  error: 5                  # blokuj commit przy ≥5

paths:
  include:
    - backend/
    - connect-*/backend/
    - packages/backend-shared-py/
  exclude:
    - "**/_pb2*.py"
    - "archive/**"
    - "tests/fixtures/**"
```

### Env vars

Brak — czysto deterministyczne tooling.

## Komendy

```bash
# Working tree vs HEAD (pre-commit)
regix compare HEAD --local                  # exit 0 = OK, non-zero = regression

# Compare dwa refs
regix compare HEAD~3 HEAD --format rich

# Output JSON+TOON do .regix/
regix compare main HEAD --output .regix/report.json

# Historia trends
regix history --commits 10

# Strict gate (CI)
regix compare HEAD~1 HEAD --fail-on error --errors-only
```

## Output

```
Regression Report: HEAD~1 → HEAD
════════════════════════════════════════════════════════════
✗ ERROR  hardware_routes.py::hardware_identify_proxy   cc  2 → 9   (+7)
✗ ERROR  shared/__init__.py::(module)                  mi  100 → 86 (-13.9)
⚠ WARN   diagnostics.py::run_check                     length  88 → 95 (+7)

Summary: 2 error(s), 1 warning(s), 0 improvement(s)
Gates: ✗ FAIL  (delta_error breached)
```

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/regix.yaml` | Konfiguracja |
| `@/home/tom/github/maskservice/c2004/scripts/regix-precommit.sh` | Wrapper pre-commit |
| `@/home/tom/github/maskservice/c2004/.pre-commit-config.yaml:65-72` | Hook `regix` |
| `@/home/tom/github/maskservice/c2004/Taskfile.yml:296-330` | 6 tasków `quality:regix*` |
| `@/home/tom/github/maskservice/c2004/pyqual.yaml:10-26` | Stage `regression-check` |

## Backend dependencies

regix używa kilku backendów (wszystkie LLM-free):

| Backend | Co liczy | Wymagane |
|---|---|---|
| `lizard` | Cyclomatic complexity, length | ✅ |
| `radon` | Maintainability Index | ✅ |
| `coverage` | Coverage % per file | optional (jeśli pytest-cov uruchomiony) |
| `vallm` | Syntax + import score | ✅ |

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `regix: command not found` | `pip install --user regix` |
| `Backend 'vallm' not available` | `pip install --user vallm` (wymaga Python 3.12+) |
| Coverage brak danych | `pytest --cov` przed `regix compare HEAD --local` |
| Zbyt wiele false positive | Edycja `regix.yaml` — `paths.exclude` lub `delta error` ↑ |
| Pre-commit hook blokuje OK commit | Sprawdź sensowność `delta error` thresholds |

## Linki

- Repo: https://github.com/semcod/regix (lokalnie: `/home/tom/github/semcod/regix`)
- Wersja: `0.1.2` (editable)
- W c2004: pre-commit + 6 Taskfile commands
