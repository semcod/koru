# Local publication: OneDev + Validator (PL / EN)

## Polski

Ta ścieżka publikuje PR **bez uruchamiania GitHub Actions na repozytorium docelowym**
(np. `semcod/koru`). Zamiast workflowów na targetcie:

1. **Standard packs / conformance** — skrypt buduje tymczasowy worktree na zamrożonym
   `head.sha` PR i uruchamia te same kroki co
   `.github/workflows/standard-pack-conformance.yml`. Po sukcesie wystawia status
   `standard packs / conformance` przez GitHub REST (`gh api statuses`).
2. **OneDev** — lokalny `onedev-agent` (`pr-coordinate-once`, `pr-execute-once`) publikuje
   dowód `onedev/local-verify` na tym samym SHA (wymaga `GITHUB_TOKEN` i skonfigurowanego
   `config/repositories.toml`).
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
2. **OneDev** — local `onedev-agent` publishes `onedev/local-verify` on that SHA.
3. **Validator** — trusted merge path is only `subactor/validator-agent`
   `dispatch-direct-pr.sh` (optional `--merge --watch`).

### Example (`semcod/koru`)

Same command block as above.

Use `--dry-run` to run checks and OneDev without REST status or Validator dispatch.

### Alternative: `koru ci publish`

`koru ci publish` focuses on Validator dispatch from the Koru CLI; use this shell script
when the target must not rely on GHA for conformance and OneDev evidence.
