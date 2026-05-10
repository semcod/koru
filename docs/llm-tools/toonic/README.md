# toonic — Universal TOON format platform for LLM-optimized files

## Co to jest

`toonic` (PyPI) to **universal TOON format converter + processor**. TOON
(Tabular Object-Oriented Notation) to LLM-friendly YAML wariant z:

- mocną kompresją struktur listowych do tabel (`name,age | john,30 | mary,25`)
- mniejszym tokenowo niż JSON/YAML dla LLM context
- czytelność dla człowieka zachowana

W koru i c2004 ekosystemie TOON jest **lingua franca** dla:

- `redup` reports (`scan.toon.yaml`, duplicate groups)
- `code2llm` outputs (`analysis.toon.yaml`, project map)
- `vallm batch` outputs
- `connect-*.toon` files w c2004 (per-module summaries)

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Convert YAML → TOON (kompresja list) | `toonic convert input.yaml -o output.toon.yaml` |
| Convert JSON → TOON | `toonic convert input.json -o output.toon.yaml` |
| Validate TOON syntax | `toonic validate file.toon.yaml` |
| Render TOON → JSON dla downstream consumers | `toonic render input.toon.yaml --to json` |
| Diff two TOON files | `toonic diff old.toon.yaml new.toon.yaml` |

## Konfiguracja

### Brak osobnego configu

Wszystko przez CLI. Format auto-detected z extension lub `--format`.

### Env vars

| Env var | Cel |
|---|---|
| `TOONIC_VERBOSE=1` | szczegółowe logi parsing |

## Komendy

```bash
toonic --version
toonic --help

# Conversion
toonic convert in.yaml -o out.toon.yaml      # auto-detect input format
toonic convert in.json --format json -o out.toon.yaml
toonic render out.toon.yaml --to json -o out.json
toonic render out.toon.yaml --to yaml         # roundtrip (drops compression)

# Validation
toonic validate file.toon.yaml                # syntax + structure
toonic validate file.toon.yaml --strict       # fail on any anomaly

# Diff (semantic — ignores list ordering when keys present)
toonic diff baseline.toon.yaml current.toon.yaml
toonic diff --layer schema baseline.toon.yaml current.toon.yaml
```

## Integracja z koru i c2004

| Plik | Format | Use case |
|---|---|---|
| `redup/scan.toon.yaml` | TOON | duplicate groups, ~70% mniejszy niż equivalent JSON |
| `code2llm/analysis.toon.yaml` | TOON | project map, classes/functions per file |
| `vallm/batch.toon.yaml` | TOON | tier-1 syntax check results |
| `connect-config.toon`, `connect-data.toon` (c2004) | TOON | per-module summary dla LLM |
| `redeploy/local/docker-compose/deployment.yaml` | YAML | markpact spec (toonic-friendly ale nie required) |

## Workflow: produce TOON → consume by LLM

```bash
# 1. Generate TOON snapshot:
redup scan . --format toon --output redup.toon.yaml
code2llm . -f toon -o project.toon.yaml

# 2. (Optional) Validate:
toonic validate redup.toon.yaml --strict

# 3. Feed do LLM (Windsurf, Cursor, Claude Code):
#    LLM agent czyta TOON natywnie — kompaktowy + zachowuje strukturę

# 4. Diff between sessions:
toonic diff redup-yesterday.toon.yaml redup.toon.yaml
```

## Reference deployment (c2004)

c2004 generuje TOON wszędzie:

- `connect-config.toon` (3 matches w SUMR), `connect-data.toon`,
  `connect-workshop.toon`, `connect-test.toon`
- `backend/project/analysis.toon.yaml`, `backend/project/calls.toon.yaml`
- `.regres/*.json` → eksportowane jako TOON dla LLM context

## Companion tools

- **`code2llm`** — natywnie wspiera `-f toon` output
- **`redup`** — `--format toon` w scan/check
- **`vallm`** — `--format toon` w batch
- **`sumd`/`sumr`** — wewnętrznie używają TOON dla calls/analysis snippets

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `toonic: command not found` | `pip install --user --upgrade toonic` |
| Roundtrip YAML→TOON→YAML traci ordering | TOON nie gwarantuje key order; jeśli ważne, użyj `--preserve-order` |
| TOON parser fail na list inside list | sprawdź indentację — TOON wymaga konsekwentnej (2 spaces zalecane) |
| `--diff --layer schema` brak output | layer-aware diff dostępny tylko gdy TOON ma annotacje `# layer: ...` |

## Linki

- Repo / PyPI: https://pypi.org/project/toonic/
- Reference: c2004 `connect-*.toon`, `redup/scan.toon.yaml`
- Companion: `code2llm` (TOON output), `redup` (TOON reports), `vallm` (batch TOON)
