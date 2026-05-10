# protogate — migration tool for legacy systems

## Co to jest

`protogate` (PyPI: `protogate>=0.1.24`) to **migration & delegation
platform** dla wyciągania bounded slices z legacy systems z minimalnym
coupling. Built on **SUMD + DOQL + testql + taskfile** ecosystem.

Pattern: **c2004-first** — c2004 (lub Twoja aplikacja) zachowuje contracts,
generators, CQRS handlers; protogate dostarcza **runtime bridge** dla
wywoływania migration tooling z aplikacji.

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Wyciągnij bounded slice z legacy monolith | `protogate extract <slice>` |
| Discover migration candidates | `protogate discover .` |
| Generate migration plan artifact | `protogate plan --output plan.toon.yaml` |
| Run migration delegation | `protogate delegate <target>` |
| Status migration | `protogate status` |

## Konfiguracja

### Architecture overview

| Owner | Co przejmuje |
|---|---|
| **Twoja app (c2004-first)** | Contracts (Protobuf), generators + schema registry, CQRS handlers, migration discovery artifacts, shell, navigation, auth/session bridge |
| **`protogate`** | Delegation/execution tooling layer, runtime bridge dla invoking migration tooling |

### Env vars

| Env var | Cel |
|---|---|
| `PROTOGATE_PROJECT` | repo root dla migration discovery |
| `PROTOGATE_VERBOSE=1` | szczegółowe logi |

## Komendy

```bash
protogate --version
protogate --help

# Discovery
protogate discover .                     # find migration candidates
protogate discover --type bounded-slice  # specific slice type

# Planning
protogate plan --output plan.toon.yaml   # migration plan artifact
protogate plan --target <module>         # plan for specific target

# Delegation
protogate delegate <target>              # invoke migration tooling
protogate status                         # progress + remaining slices
```

## Integracja z koru

Protogate jest **companion** dla `redeploy` + `sumd` + `doql`:

```text
sumd        → identify code structure (SUMR.md)
doql        → declare bounded slice intended state
protogate   → extract + delegate migration
redeploy    → apply new state to target environment
testql      → verify endpoints survived migration
```

Pełny workflow legacy migration:

```bash
# 1. Discover what to migrate
sumd .                                   # SUMR.md baseline
protogate discover .                     # candidates list
redup scan . --format toon               # duplicate analysis

# 2. Plan
protogate plan --target order-service \
  --output plans/order-service.toon.yaml

# 3. Execute
protogate delegate order-service

# 4. Verify
testql run scenarios/order-service.toon.yaml

# 5. Snapshot new state
doql adopt . -o app.doql.less
```

## Reference

- Repo / PyPI: https://pypi.org/project/protogate/
- Wersja: `protogate==0.1.24`
- Built on: `sumd` + `doql` + `testql` + Taskfile
- Use case: extracting bounded slices z monolith do microservices

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `protogate: command not found` | `pip install --user --upgrade protogate` |
| `discover` zwraca pustą listę | sprawdź `PROTOGATE_PROJECT` lub uruchom z głównego dir repo |
| Plan generation timeout | duży monorepo — użyj `--scope <subdir>` |
