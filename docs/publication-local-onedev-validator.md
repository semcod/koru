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
3. **Validator** — jedyne zaufane workflow GitHub Actions to dispatch na
   `subactor/validator-agent` (`bin/dispatch-direct-pr.sh`), który czeka na checki i
   opcjonalnie merge (`--merge --watch`).

### Przykład (`semcod/koru`)

```bash
export ONEDEV_AGENT="$HOME/github/subactor/onedev-agent"
export VALIDATOR_AGENT="$HOME/github/subactor/validator-agent"
export GITHUB_TOKEN="$(gh auth token)"

./scripts/publish-local-onedev-validator.sh \
  --owner semcod --name koru --pr 123 --ticket ticket-065 --merge
```

Użyj `--dry-run`, aby wykonać checki i OneDev bez statusu REST ani dispatchu Validatora.

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
3. **Validator** — trusted merge path is only `subactor/validator-agent`
   `dispatch-direct-pr.sh` (optional `--merge --watch`).

### Example (`semcod/koru`)

Same command block as above.

Use `--dry-run` to run checks and OneDev without REST status or Validator dispatch.

Operational report (2026-09-02 tests and merges): [publication-local-onedev-validator-report.md](./publication-local-onedev-validator-report.md).

### Alternative: `koru ci publish`

`koru ci publish` focuses on Validator dispatch from the Koru CLI; use this shell script
when the target must not rely on GHA for conformance and OneDev evidence.
