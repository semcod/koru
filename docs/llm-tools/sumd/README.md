# sumd / sumr — LLM refactor snapshots

## Co to jest

`sumd` (PyPI package, provides both `sumd` and `sumr` CLIs) generuje
**LLM-readable descriptors** projektu:

| CLI | Output | Profile | Cel |
|---|---|---|---|
| `sumd .` | `SUMD.md` | descriptor (default) | ogólny snapshot projektu dla LLM — struktury, endpointy, manifesty, konfiguracje |
| `sumr .` | `SUMR.md` | refactor | snapshot zorientowany na **refactoring** — complexity hotspots, duplicates, migration hints |

Internally `sumr .` ≡ `sumd scan . --profile refactor`.

## Kiedy używać

`SUMR.md` to **trzeci tier dokumentacji** po `README.md` i `SUMD.md`:

- **`README.md`** — czytelny dla człowieka, stabilny.
- **`SUMD.md`** — pełny descriptor, update gdy zmienia się struktura repo.
- **`SUMR.md`** — refactor-focused, update po **dużych chunkach refaktoru**
  (tygodniowo / co 25+ commitów) → LLM agent może szybko zobaczyć gdzie
  są hotspots, duplicates, migration candidates.

Nie chcesz odpalać `sumr .` po każdym commicie — jest drogi (~30-90s,
uruchamia code2llm + redup + doql-sync), a output driftuje powoli. Stąd
wzorzec **debounced refresh** zamiast eager regeneration.

## Konfiguracja

### Brak osobnego configu

Wszystko przez env vars w orchestration layer (patrz sekcja "Integracja"):

| Env var | Default | Efekt |
|---|---|---|
| `SUMR_MAX_COMMITS` | 25 | Refresh trigger: N commitów od ostatniego SUMR.md commita |
| `SUMR_MAX_DAYS` | 7 | Refresh trigger: dni od mtime SUMR.md |
| `SUMR_FORCE` | 0 | Gdy `1`, ignoruje debounce |
| `SUMR_SKIP_DEPS` | 0 | Gdy `1`, pomija `pip install --upgrade sumd code2llm redup doql` |
| `SUMR_VENV` | `venv` | Ścieżka do venv-a z `sumr` binary |

## Komendy

```bash
# Bezpośrednie CLI (drogie — zawsze regeneruje)
venv/bin/sumd .              # pełny descriptor → SUMD.md
venv/bin/sumr .              # refactor profile → SUMR.md
venv/bin/sumr --help         # opcje (--analyze, --tools, --no-raw, ...)

# Debounced wrapper (rekomendowane — patrz template)
scripts/sumr-refresh.sh           # refresh tylko gdy stale
scripts/sumr-refresh.sh --force   # zawsze refresh
scripts/sumr-refresh.sh --status  # diagnostyka staleness, exit 1 gdy stale
```

## Integracja z repo (3-warstwowy pattern)

`sumd` sam w sobie to tylko CLI. Koru dostarcza orchestration layer, który
opakowuje go w **debounced refresh z automatycznym odświeżaniem**:

| Warstwa | Kiedy | Template |
|---|---|---|
| **Manual** | na żądanie, `task quality:sumr:refresh` | [`templates/sumr-refresh.sh.template`](../../../templates/sumr-refresh.sh.template) |
| **Lokalny hook** | `post-merge` / `post-commit` — po `git pull` / commit | [`templates/git-hooks/post-merge.template`](../../../templates/git-hooks/post-merge.template) |
| **Global CI** | weekly cron, PR-bot | [`templates/sumr-weekly.yml.template`](../../../templates/sumr-weekly.yml.template) |

Wszystkie trzy warstwy używają tego samego `scripts/sumr-refresh.sh` z
jednolitą logiką debounce — jeśli lokalny regenerował niedawno i
wypushował, weekly CI widzi fresh state i skipuje PR.

Pełny workflow: [`workflows/sumr-refresh-loop.md`](../../../workflows/sumr-refresh-loop.md).

## Reference deployment (c2004)

Produkcyjny deployment w `maskservice/c2004`:

| Plik | Rola |
|---|---|
| `scripts/sumr-refresh.sh` | debounced refresh wrapper (~188 linii) |
| `scripts/git-hooks/post-merge` | branch-aware (tylko `main`), async bg, non-blocking |
| `scripts/git-hooks/post-commit` | lekki hint wariant (bez auto-refresh) |
| `scripts/git-hooks/install.sh` | idempotentny installer z marker-based uninstall |
| `.github/workflows/sumr-weekly.yml` | Monday 04:00 UTC cron + PR-bot |
| `Taskfile.yml` → `quality:sumr:*` | 5 task entry pointów (`status`, `auto`, `refresh`, `install-hook`, `uninstall-hook`) |
| `.gitignore` → `.sumr/` | state dir (post-merge.log, state.json) |

Empirycznie w c2004: SUMR.md ≈ 702kB, regeneracja ~30s bez `--analyze`,
trigger średnio 1×/tydzień po debounce.

## Zależności których `sumr` używa

`sumr` może wywołać (zależnie od flag):

| Dep | Kiedy | Flag |
|---|---|---|
| `sumd` | zawsze | — |
| `code2llm` | przy `--analyze` | `--tools code2llm,...` |
| `redup` | przy `--analyze` | `--tools ...,redup,...` |
| `vallm` | przy `--analyze` (skip z `--tools code2llm,redup`) | `--tools ...,vallm` |
| `doql` | default (można `--no-doql-sync`) | `--doql-sync` |

Rekomendowany subset do `pip install --upgrade` przed refresh:
**`sumd code2llm redup doql`** (bez `vallm` — heavy LLM deps, off by default).

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `sumr: command not found` | `pip install --user sumd` (pakiet nazywa się `sumd`, dostarcza oba CLI) |
| "🔍 Scanning 0 projects" | repo nie ma marker file — dodaj `pyproject.toml`, `package.json`, `Taskfile.yml` lub `SUMD.md` |
| SUMR.md nie regeneruje po refaktorze | sprawdź `scripts/sumr-refresh.sh --status` — może commits<25 i days<7 (fresh) |
| Hook `post-merge` odpala się na feature branch | **by design** — wzorzec tylko dla `main`/`master`. Manual trigger: `task quality:sumr:refresh` |
| Weekly CI nie otwiera PR | check `.github/workflows/sumr-weekly.yml` uprawnienia (`contents: write`, `pull-requests: write`) |

## Linki

- Repo / PyPI: https://pypi.org/project/sumd/
- Wersja (2026-05-10): `sumd==0.3.45`
- Reference deployment: [`maskservice/c2004`](https://github.com/maskservice/c2004) — 702kB SUMR.md, 3-warstwowy refresh
