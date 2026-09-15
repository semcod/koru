# Local publication: OneDev + Validator (PL / EN)

## Przygotowanie zakresu / Scope preparation

Commit musi powstać w osobnym worktree na gałęzi `ticket/NNN-...`, powiązanej
z rzeczywistym `IN_PROGRESS` ticketem. Hook odrzuca commit z `main`.
`intent.json` musi obejmować dokładnie dostarczane pliki i ich workstream.
Zmiany spoza zakresu należy rozdzielić do osobnych ticketów; sama zmiana
nazwy gałęzi nie naprawia błędów `GOV-SCOPE` ani `GOV-WORKSTREAM`.

Odśwież `origin/main`, sprawdź nakładanie zakresów i uruchom zarządzaną bramkę.
Nie przepinaj `acceptedBaseSha` automatycznie na najnowszy SHA: zmieniaj go
wyłącznie po rzeczywistym odświeżeniu bazy i ponownym przeglądzie zakresu.

Create commits in a dedicated ticket worktree. Use the same ticket for the
intent, branch, PR and Validator dispatch. Preserve local queue/environment
snapshots separately from implementation changes. A passing local check or
this guide is not trusted merge approval.

## Polski

Ta ścieżka publikuje PR **bez uruchamiania GitHub Actions na repozytorium docelowym**
(np. `semcod/koru`). Zamiast workflowów na targetcie:

1. **Standard packs / conformance** — skrypt buduje tymczasowy worktree na zamrożonym
   `head.sha` PR i uruchamia te same kroki co
   `.github/workflows/standard-pack-conformance.yml`. Po sukcesie wystawia status
   `standard packs / conformance` przez GitHub REST (`gh api statuses`).
2. **OneDev** — ten sam profil testów co `onedev-agent` (`config/repositories.toml`)
   uruchamiany lokalnie w worktree; status `onedev/local-verify` idzie przez REST.
   Wymaga sibling `subactor/subllm` tylko gdy używasz pełnego agenta; domyślnie
   skrypt odpala bramki profilu bez root/docker executora.
3. **Validator** — zaufana ścieżka publikacji prowadzi przez wdrożony lokalny
   adapter `run-local-direct-pr.sh`. Dostaje pełny slug repozytorium, numer PR,
   ticket, zamrożony `head.sha` i chroniony klucz Validator App; `--merge` wykonuje
   zatwierdzenie i scalenie dopiero po sprawdzeniu exact-head oraz wymaganych bramek.

### Przykład (`semcod/koru`)

```bash
export ONEDEV_AGENT="$HOME/github/subactor/onedev-agent"
export GITHUB_TOKEN="$(gh auth token)"

./scripts/publish-local-onedev-validator.sh \
  --owner semcod --name koru --pr 123 --ticket ticket-065 --merge
```

Skrypt ładuje chronione środowisko lokalnego Validatora z
`$HOME/.config/subactor/local-validator.env` (można zmienić przez
`LOCAL_VALIDATOR_ENV_FILE`). Użyj `--dry-run`, aby wykonać checki i OneDev bez
statusu REST ani publikacji przez Validatora.

Szczegółowy raport z testów i publikacji (2026-09-02): [publication-local-onedev-validator-report.md](./publication-local-onedev-validator-report.md).

### Alternatywa: `koru ci publish`

W katalogu Koru wrapper `koru ci publish --ticket ticket-NNN` deleguje głównie do
Validator dispatch (freeze head, `--wait-checks`, opcjonalnie `--merge`). Nie zastępuje
lokalnych standard packów ani pełnego cyklu OneDev — użyj tego skryptu, gdy target nie
ma polegać na GHA dla conformance + `onedev/local-verify`.

---

## English

This path publishes a PR **without running GitHub Actions on the target repository**
(e.g. `semcod/koru`). Instead of target-repo workflows:

1. **Standard packs / conformance** — a temp worktree at the frozen PR `head.sha` runs the
   same steps as `.github/workflows/standard-pack-conformance.yml`, then posts
   `standard packs / conformance` via GitHub REST.
2. **OneDev** — runs the same repository profile test gates locally in the worktree,
   then posts `onedev/local-verify` via REST (no target-repo GHA, no root-only executor).
3. **Validator** — the trusted merge path is the deployed local
   `run-local-direct-pr.sh` adapter. It receives the repository, PR, ticket,
   frozen head and protected App key explicitly; `--merge` performs the
   exact-head verification and protected merge.

### Example (`semcod/koru`)

Use the same command block as above. The script loads the protected local
Validator environment from `$HOME/.config/subactor/local-validator.env`.

Use `--dry-run` to run checks and OneDev without REST status or Validator
publication.

Operational report (2026-09-02 tests and merges): [publication-local-onedev-validator-report.md](./publication-local-onedev-validator-report.md).

### Alternative: `koru ci publish`

`koru ci publish` is a separate Koru CLI path and still resolves its own
Validator launcher. Use this shell script for the complete local conformance,
OneDev and protected Validator cycle when the target must not rely on GHA.
