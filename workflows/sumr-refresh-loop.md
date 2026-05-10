---
description: Debounced 3-layer refresh of SUMR.md (LLM refactor snapshot)
---

# SUMR refresh loop

Wzorzec odświeżania `SUMR.md` (LLM-readable refactor descriptor
generowany przez `sumr .`) — **rzadko, automatycznie, bezpiecznie**.

`SUMR.md` jest drogi do wygenerowania (~30-90s, wywołuje `code2llm`,
`redup`, `doql sync`) i driftuje powoli, więc nie chcemy regenerować go
po każdym commicie. Zamiast tego trzy warstwy, wszystkie używające tej
samej debounced logiki:

```text
┌─────────────────┬────────────────────────────┬────────────────────┐
│ Warstwa         │ Trigger                    │ Częstotliwość      │
├─────────────────┼────────────────────────────┼────────────────────┤
│ 1. Manual       │ `task quality:sumr:refresh`│ ad-hoc (force)     │
│ 2. Lokalny hook │ git post-merge on main     │ po `git pull`      │
│ 3. Global CI    │ GitHub Actions weekly cron │ Monday 04:00 UTC   │
└─────────────────┴────────────────────────────┴────────────────────┘
        ↓                    ↓                          ↓
        └──── wspólny: scripts/sumr-refresh.sh ─────────┘
                         (debounce + refresh)
```

Debounce triggery (każdy jako OR):

- `SUMR.md` nie istnieje
- ≥ `SUMR_MAX_COMMITS=25` commitów na HEAD od czasu ostatniego dotknięcia `SUMR.md`
- ≥ `SUMR_MAX_DAYS=7` dni od `mtime SUMR.md`
- `--force` / `SUMR_FORCE=1`

## Deployment checklist — wdrożenie w swoim repo

Wykonaj od góry do dołu. Każdy krok jest idempotentny (można uruchomić
wielokrotnie bez efektów ubocznych).

### Shortcut — jeśli masz `koru` sklonowane lokalnie

Dla repo zewnętrznego (np. `~/github/myproject`):

```bash
# Ustaw ścieżkę do koru (gdzie są templates/) i przejdź do swojego repo
KORU=/home/you/github/semcod/koru
cd ~/github/myproject

# Krok 1 — sumd binary
bash "$KORU/docs/llm-tools/sumd/install.sh"

# Kroki 3+5+6+7 — skopiuj wszystkie templates w jednym ruchu
mkdir -p scripts/git-hooks .github/workflows
cp "$KORU/templates/sumr-refresh.sh.template"           scripts/sumr-refresh.sh
cp "$KORU/templates/git-hooks/post-merge.template"      scripts/git-hooks/post-merge
cp "$KORU/templates/git-hooks/post-commit.template"     scripts/git-hooks/post-commit
cp "$KORU/templates/git-hooks/install.sh.template"      scripts/git-hooks/install.sh
cp "$KORU/templates/sumr-weekly.yml.template"           .github/workflows/sumr-weekly.yml
chmod +x scripts/sumr-refresh.sh scripts/git-hooks/*
grep -qxF '.sumr/' .gitignore 2>/dev/null || echo '.sumr/' >> .gitignore

# Krok 4 — wklej quality:sumr:* tasks do Taskfile.yml (zobacz sekcję Krok 4)

# Krok 2 — pierwszy SUMR.md + Krok 5 — hook
scripts/sumr-refresh.sh --force
bash scripts/git-hooks/install.sh post-merge

# Zatwierdzenie
git add SUMR.md scripts .github .gitignore Taskfile.yml
git commit -m "feat(sumr): bootstrap 3-layer SUMR.md refresh"
```

Dla wdrożenia **w samym koru** (dogfood): użyj `task template:install:sumr`,
który wykonuje kroki 3+5+6+7 jednym taskiem (templates są już w miejscu).

Każdy krok poniżej objaśnia **dlaczego** i **co weryfikować** dla manual
użytkowników.

### Krok 1. Zainstaluj `sumd` + `sumr`

```bash
bash docs/llm-tools/sumd/install.sh
# albo ręcznie:
pip install --user --upgrade sumd
```

Weryfikacja:

```bash
sumd --version
sumr --help | head -5
```

### Krok 2. Wygeneruj pierwszy `SUMR.md`

```bash
sumr .
git add SUMR.md
git commit -m "chore(sumr): initial SUMR.md snapshot"
```

To daje debounce'owi baseline do porównania.

**Uwaga — side-effects `sumr`:** oprócz `SUMR.md`, narzędzie może
wygenerować w repo:

- `app.doql.less` — DOQL boilerplate (plus `app.doql.css` dla frontendów)
- `project/` — raporty `code2llm` (TOON-format)
- `testql-scenarios/` — wygenerowane scenariusze `testql`

`sumr-weekly.yml` commituje tylko `SUMR.md` + `app.doql.*`. Pozostałe
pliki sam zdecyduj czy commitować. Jeśli `project/` i `testql-scenarios/`
chcesz ignorować lokalnie:

```bash
grep -qxF 'project/' .gitignore 2>/dev/null || echo 'project/' >> .gitignore
grep -qxF 'testql-scenarios/' .gitignore 2>/dev/null || echo 'testql-scenarios/' >> .gitignore
```

### Krok 3. Zainstaluj debounced wrapper

```bash
mkdir -p scripts
cp templates/sumr-refresh.sh.template scripts/sumr-refresh.sh
chmod +x scripts/sumr-refresh.sh
```

Smoke test:

```bash
scripts/sumr-refresh.sh --status
# Oczekiwane: [sumr-refresh] SUMR.md state: fresh:commits=0/25,days=0/7
# Exit code: 0
```

### Krok 4. Wpisz `quality:sumr:*` taski do `Taskfile.yml`

Dodaj do swojego `Taskfile.yml`:

```yaml
quality:sumr:status:
  desc: "Show SUMR.md staleness vs HEAD (LLM-free; exit 1 if stale)"
  cmds:
    - scripts/sumr-refresh.sh --status

quality:sumr:auto:
  desc: "Refresh SUMR.md only if stale (debounced; safe for hooks/cron)"
  cmds:
    - scripts/sumr-refresh.sh

quality:sumr:refresh:
  desc: "Force-refresh SUMR.md (bumps sumd/code2llm/redup/doql + regenerates)"
  cmds:
    - scripts/sumr-refresh.sh --force

quality:sumr:install-hook:
  desc: "Install git post-merge hook (HOOK=post-commit|both for alt)"
  cmds:
    - bash scripts/git-hooks/install.sh {{.HOOK | default "post-merge"}}

quality:sumr:uninstall-hook:
  desc: "Remove c2004 sumr-refresh git hooks (leaves foreign hooks intact)"
  cmds:
    - bash scripts/git-hooks/install.sh --uninstall
```

### Krok 5. Zainstaluj git hooks (warstwa 2)

```bash
mkdir -p scripts/git-hooks
cp templates/git-hooks/post-merge.template scripts/git-hooks/post-merge
cp templates/git-hooks/post-commit.template scripts/git-hooks/post-commit
cp templates/git-hooks/install.sh.template scripts/git-hooks/install.sh
chmod +x scripts/git-hooks/*

task quality:sumr:install-hook          # default: post-merge
# lub:
task quality:sumr:install-hook HOOK=both
```

Weryfikacja:

```bash
ls -la .git/hooks/post-merge
# Oczekiwane: executable, zawiera "c2004 sumr-refresh" marker
```

### Krok 6. Zainstaluj weekly CI (warstwa 3)

```bash
mkdir -p .github/workflows
cp templates/sumr-weekly.yml.template .github/workflows/sumr-weekly.yml
```

Następnie:

1. Edit `.github/workflows/sumr-weekly.yml`:
   - Opcjonalnie dostosuj cron (`0 4 * * 1` → inny dzień/godzina)
   - Opcjonalnie dostosuj `add-paths` (jeśli `sumr` generuje u Ciebie
     też `app.doql.css` lub inne pliki)

2. (Opcjonalnie) Dodaj `SUMR_PAT` secret do repo:
   - GH → Settings → Secrets and variables → Actions → New secret
   - Bez PAT: workflow działa z domyślnym `GITHUB_TOKEN` (PRs nie
     trigger-ują downstream workflows, co jest OK bo nic nie keyuje
     się na SUMR.md).

3. Commit i push:

   ```bash
   git add .github/workflows/sumr-weekly.yml
   git commit -m "ci(sumr): add weekly SUMR.md refresh workflow"
   git push
   ```

### Krok 7. Uzupełnij `.gitignore`

Idempotentnie (grep zapobiega duplikatom):

```bash
grep -qxF '.sumr/' .gitignore 2>/dev/null || echo '.sumr/' >> .gitignore
git add .gitignore
git commit -m "chore(gitignore): ignore .sumr/ state dir"
```

`.sumr/` zawiera lokalny state debounce'a (`state.json`,
`post-merge.log`, `post-merge.lock`) — nie commit-ować.

Jeśli używasz `task template:install:sumr` — ten krok wykonuje się
automatycznie (`.gitignore` jest aktualizowany przez zadanie).

### Krok 8. (Opcjonalnie) Dodaj `sumd` do `install:tools`

Jeśli masz `install:tools` task w Taskfile:

```yaml
install:tools:
  desc: Install all underlying LLM tools
  cmds:
    - pip install planfile regix redup vallm prefact pfix sumd  # ← dodaj sumd
```

### Krok 9. Weryfikacja end-to-end

```bash
# sumd binary dostępny
sumd --version || echo "FAIL: sumd missing (Krok 1)"
sumr --help >/dev/null && echo "OK: sumr help works"

# SUMR.md jest w repo
test -s SUMR.md && echo "OK: SUMR.md $(wc -c < SUMR.md) bytes"

# Warstwa 1 — debounced wrapper
task quality:sumr:status
# Oczekiwane: fresh:commits=0/25,days=0/7 → exit 0

# Warstwa 2 — hook aktywny (jeśli zainstalowany)
test -x .git/hooks/post-merge && \
  grep -q 'c2004 sumr-refresh' .git/hooks/post-merge && \
  echo "OK: post-merge hook installed and ours"

# Warstwa 3 — workflow YAML valid (jeśli zainstalowany)
test -f .github/workflows/sumr-weekly.yml && \
  python3 -c "import yaml; yaml.safe_load(open('.github/workflows/sumr-weekly.yml'))" && \
  echo "OK: weekly workflow YAML valid"

# .gitignore has .sumr/
grep -qxF '.sumr/' .gitignore && echo "OK: .sumr/ is gitignored"
```

## Troubleshooting deployment

| Problem | Rozwiązanie |
|---|---|
| `sumr: command not found` po install.sh | Sprawdź `$PATH` — `pip install --user` daje `~/.local/bin`. Dodaj do PATH lub użyj `SUMD_PIP_SCOPE=venv` w install.sh |
| `scripts/sumr-refresh.sh --status` daje błąd `git: not a repo` | Skrypt MUSI być w repo — sprawdź `git rev-parse --show-toplevel` |
| Hook odpala się na feature branch mimo filtra | Sprawdź `git rev-parse --abbrev-ref HEAD` — filtr pattern matching `main\|master`, jeśli masz inny default branch → edytuj hook |
| Weekly CI workflow timeouts | Default `timeout-minutes: 15` — zwiększ jeśli `sumr .` u Ciebie trwa dłużej (duży monorepo) |
| Concurrent pulls race-ują hooks | **by design**: `flock` zapewnia queueing. Sprawdź `.sumr/post-merge.lock` |

## Odroll / disable

```bash
# Wyłącz local hook:
task quality:sumr:uninstall-hook

# Wyłącz weekly CI:
rm .github/workflows/sumr-weekly.yml
git commit -am "chore: disable sumr weekly refresh"

# Zostaw manual-only:
# (nic nie trzeba robić — `task quality:sumr:refresh` zawsze dostępny)
```

## Dlaczego trzy warstwy?

- **Manual (1)** — dla ad-hoc regeneracji po dużym refaktorze przed PR.
- **Lokalny hook (2)** — refresh u tych, którzy pull-ują main często;
  daje team'owi kontrybutorskiemu świeży snapshot bez czekania na CI.
- **Global CI (3)** — safety net: jeśli nikt lokalnie nie trigger-uje,
  weekly cron dogaduje PR z bezpiecznym review window.

Debounce w `scripts/sumr-refresh.sh` łączy te warstwy: jeśli lokalny
hook niedawno regenerował i commitował, CI widzi fresh state i
grace-skipuje. Brak deduplikacji pracy.

## Reference implementation

Wszystkie templates w tym folderze są kopiami z
[`maskservice/c2004`](https://github.com/maskservice/c2004), gdzie
pattern działa produkcyjnie od 2026-05-10. Metryki:

- 702kB SUMR.md, ~30s regeneracja bez `--analyze`
- Hook cost przy fresh state: ~28ms (git rev-parse + fs stat)
- Hook cost przy stale: ~10ms (spawn bg setsid + return)
- Weekly CI: ~2 min total (setup-python cache + sumr + diff + PR)
