# goal — automated git push + smart commits + release workflow

## Co to jest

`goal` (PyPI: `goal>=2.1.241`) to **enterprise-grade commit intelligence**
+ automated git push z deep code analysis. Generuje conventional commits,
zarządza versioning (semver/calver), aktualizuje CHANGELOG.md i orchestruje
release workflow.

W koru `goal` jest **w użyciu od początku** — `goal.yaml` (root) konfiguruje
versioning rules, conventional commit templates, domain mapping, quality
gates dla commit messages.

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Zaproponuj smart commit message z diff'a | `goal commit` |
| Pełny release workflow (tests + push + publish) | `goal -a` |
| Tylko commit z auto-bumpem patch | `goal --bump patch` |
| Dry-run (zobacz co się stanie) | `goal --dry-run` |
| Sprawdź spójność wersji w plikach | `goal check-versions` |
| Auto-fix project config (doctor) | `goal doctor` |
| Bootstrap deps + venv | `goal bootstrap` |
| Init pre-commit hooks | `goal hooks install` |

## Konfiguracja

### `goal.yaml` (root projektu)

Główne sekcje:

```yaml
version: '1.0'
project:
  name: <APP_NAME>
  type: [python]
  description: <one-liner>

versioning:
  strategy: semver           # albo calver
  files:
    - pyproject.toml:version
    - package.json:version
  bump_rules:
    patch: 10                # threshold w commitach
    minor: 50
    major: 200

git:
  commit:
    strategy: conventional   # feat/fix/docs/test/refactor/...
    scope: <APP_NAME>        # automatic scope
    abstraction_level: auto  # high / medium / low
    domain_mapping:
      src/*.py: core
      tests/*: test
      docs/*: docs
      .github/*: ci

  changelog:
    enabled: true
    template: keep-a-changelog
    output: CHANGELOG.md

quality:
  commit_summary:
    min_value_words: 3
    max_generic_terms: 0     # bans: "update", "fix", "improve"
    required_metrics: 2

  gates:
    max_complexity_percent: 200
    min_capabilities: 1
    max_banned_words: 0
```

### Env vars

| Env var | Cel |
|---|---|
| `PYPI_TOKEN` | publish do PyPI (`goal --publish`) |
| `NPM_TOKEN` | publish do npm |
| `GH_TOKEN` | release notes via GitHub API |

## Komendy

```bash
goal --version                    # 2.1.241+
goal --help                       # all subcommands

# Smart commit (90% use case)
goal commit                       # generuj smart message + commit
goal commit --dry-run             # podgląd

# Pełny workflow
goal -a                           # tests + commit + push + publish
goal -a --no-publish              # bez publish
goal --bump minor                 # explicit bump

# Diagnostyka
goal doctor                       # auto-fix config issues
goal check-versions               # spójność wersji w plikach
goal authors list                 # team members from git history

# Rzadziej:
goal bootstrap                    # install deps for project type
goal clone <url>                  # git clone + bootstrap
goal hooks install                # pre-commit hooks (ruff, regix...)
goal config show                  # current effective config
```

## Integracja z koru

| Plik | Rola |
|---|---|
| `goal.yaml` (root) | Pełna konfiguracja koru pod goal |
| `pyproject.toml:version` | source of truth dla wersji |
| `CHANGELOG.md` | auto-updated przez `goal commit` (Keep-a-Changelog format) |
| `Taskfile.yml` | brak osobnego `task goal:*` — `goal` jest top-level CLI |

W koru pełen workflow:

```bash
# 1. Coś zmieniłeś w src/
git status

# 2. goal analizuje diff i proponuje conventional commit:
goal commit
# → "feat(core): add new feature X with metrics Y/Z"

# 3. Auto-update CHANGELOG.md w sekcji [Unreleased] / Added
# 4. Optional: goal -a żeby od razu push + tag + publish PyPI
```

## Reference deployment (c2004)

Produkcyjnie w `maskservice/c2004`:

| Plik | Rola |
|---|---|
| `goal.yaml` | identyczny pattern jak koru — versioning, commit, changelog |
| `VERSION` | source of truth dla version (1.0.36) |
| `scripts/check-version-drift.sh` | dodatkowa walidacja zgodności VERSION ↔ pyproject.toml ↔ package.json ↔ .env (SSOT enforcement) |
| Pre-commit hook | uruchamia `goal commit` w trybie validate-only |

## Companion tools

`goal` współpracuje z:

- **`costs`** — auto-add badge `AI Cost: $X.XX` do README.md przy każdym `goal commit`
- **`nfo`** — structured logging dla goal output (`--nfo-format json`)
- **`pre-commit`** — `goal hooks install` zakłada pre-commit hooks dla regix/redsl/ruff

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `goal: command not found` | `pip install --user --upgrade goal` |
| "No version drift detected" gdy jest | `goal check-versions --verbose` pokaże mismatch lub plik bez `version:` field |
| Commit message zawiera "update" / "fix" | `quality.commit_summary.generic_terms` w `goal.yaml` blokuje generic terms; przepisz |
| `goal -a` zawisa na `pytest` | używa `strategies.python.test` z `goal.yaml` — uruchom ręcznie `pytest -q --maxfail=1 tests/` i napraw pierwszy błąd |
| `ModuleNotFoundError` w `tests/tests/test_*_tests.py::test_import` | zaktualizuj `goal` do >=2.1.241; usuń zagnieżdżony scaffold lub zmień import na `tests` — patrz goal `docs/troubleshooting.md` |
| Bump version niezgodny z conventional commits | sprawdź `versioning.bump_rules` (patch=10 = wystarczy 10 nieprzyłapanych zmian dla bumpa) |

Szybka ścieżka dla koru (najkrótszy feedback loop):

```bash
# 1) szybki test fail-fast zamiast pełnego goal -a
pytest -q --maxfail=1 tests/

# 2) commit po przejściu testów
goal commit

# 3) pełny workflow dopiero gdy lokalnie jest zielono
goal -a
```

## Linki

- Repo / PyPI: https://pypi.org/project/goal/
- Wersja (2026-06-03): `goal==2.1.241` (fix scaffold importów w katalogu `tests/`)
- Reference: koru `goal.yaml` (510 linii, pełna konfiguracja); c2004 `goal.yaml`
- Companion: `costs` (cost badges), `nfo` (logging), pre-commit framework
