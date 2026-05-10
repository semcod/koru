# op3 — Layered operations tree (observe, diff, orchestrate)

## Co to jest

`op3` (PyPI: `op3>=0.2.5`) to **layered infrastructure observation engine** —
deterministic scanning + diff + orchestration infrastruktury jako dane.
Built on **fraq** fractal data primitives.

Sześć warstw obserwacji (od fizycznej do biznesowej):

| Layer | Co obserwuje |
|---|---|
| **Physical** | Hardware, displays, network, compute |
| **OS** | Kernel, system configuration |
| **Runtime** | Containers, compositor (Wayland/X) |
| **Service** | systemd services, podman/docker containers |
| **Endpoint** | HTTP endpoints, TCP ports listening |
| **Business** | Application health, business logic |

W koru `op3` jest **companion-em** dla `redeploy` i `doql` — generuje deep
multi-layer snapshot device-u ponad to, co `doql adopt` daje samo.

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Pełny scan device-u (wszystkie warstwy) | `op3 scan user@host` |
| Scan tylko konkretnych warstw | `op3 scan user@host --layers physical,service` |
| Diff dwóch snapshotów (drift) | `op3 diff old.yaml new.yaml` |
| Convert migration.yaml ↔ snapshot.yaml | `op3 convert migration.yaml --to snapshot` |
| Eksport jako `app.doql.less` | `op3 scan ... --format less > app.doql.less` |
| Pythonic API (custom probe) | `from opstree import LayerTree, scan_device` |

## Konfiguracja

### Brak osobnego configu

Wszystko przez CLI flags i Pythonic API. Layer registry definiowany w kodzie:

```python
from opstree import LayerTree, scan_device
from opstree.layers.builtin import (
    PhysicalLayer, OsLayer, RuntimeLayer,
    ServiceLayer, EndpointLayer, BusinessLayer,
)

tree = LayerTree()
tree.register(PhysicalLayer.display)
tree.register(PhysicalLayer.network)
tree.register(OsLayer.kernel)
tree.register(RuntimeLayer.container)
tree.register(ServiceLayer.systemd)
tree.register(EndpointLayer.http)
tree.register(BusinessLayer.health)

# Scan local or remote
snapshot = scan_device("pi@192.168.188.109", ssh_execute, tree)
print(snapshot.to_yaml())
```

### Env vars

| Env var | Cel |
|---|---|
| `OP3_VERBOSE=1` | szczegółowe logi probe execution |
| `OP3_TIMEOUT=10` | per-probe timeout (sekundy) |

## Komendy

```bash
op3 --version
op3 --help

# CLI scan
op3 scan localhost                       # scan local machine
op3 scan pi@192.168.188.109              # scan remote (SSH)
op3 scan host --layers physical,service  # tylko wybrane warstwy
op3 scan host --format yaml -o snap.yaml
op3 scan host --format less              # zamiast yaml → app.doql.less syntax

# Convert między formatami
op3 convert migration.yaml --to snapshot      # markpact → op3 snapshot
op3 convert app.doql.less --to snapshot       # doql LESS → snapshot
op3 convert snap.yaml --to less > app.doql.less

# Drift detection
op3 diff baseline.yaml current.yaml      # diff dwóch snapshotów
op3 diff --layer service old.yaml new.yaml  # diff per-layer
```

## Format Adapters

Trzy primary formaty — każdy ma adapter do/z `Snapshot` (immutable data class):

| Format | Adapter | Use case |
|---|---|---|
| `app.doql.less` | `LessAdapter` | DOQL declarative state (LESS-syntax) |
| `migration.yaml` | `MigrationAdapter` | markpact-style deployment specs |
| `snapshot.yaml` | `SnapshotAdapter` | natywny op3 (canonical, najpełniejszy) |

```python
from opstree.formats.less import LessAdapter

adapter = LessAdapter()
partial = adapter.parse(open("app.doql.less").read())
less_output = adapter.render(snapshot)
```

## Integracja z koru

| Plik | Rola |
|---|---|
| `templates/redeploy/device/manifest.yaml.template:108-118` | wspomina "op3-style scan" w `phase: detect` |
| `templates/redeploy/device/diagnose.md.template` | może być rozszerzony o `op3 scan host --format yaml` jako step |
| `Taskfile.yml` → potencjalny `deploy:scan DEVICE_HOST=user@host` | `op3 scan {{.DEVICE_HOST}} -o snapshots/<host>.yaml` |
| `app.doql.less` (root) | `op3 scan ... --format less` może wygenerować plik podobny do `doql adopt` |

## Workflow: deploy → scan → diff loop

```
1. redeploy run <device>/migration.md      # apply intended state
                ↓
2. op3 scan user@host -o snapshots/<host>-after.yaml
                ↓
3. op3 diff snapshots/<host>-before.yaml \
            snapshots/<host>-after.yaml   # zobacz co faktycznie zmieniło się
                ↓
4. doql adopt --from-device user@host -o app.doql.less    # update intended
                ↓
5. git commit (snapshot + app.doql.less + migration.md changes)
```

`op3` daje **deeper observability niż `doql adopt`**: hardware state,
compositor session, GPIO config, kiosk Chromium PID — rzeczy które `doql`
domyślnie pomija jako "below app level".

## Reference deployment (c2004)

Produkcyjnie w `maskservice/c2004`:

| Plik | Rola |
|---|---|
| `redeploy/pi109/manifest.yaml:108-118` | `tool_hint: doql adopt OR redeploy detect` — op3 fits tutaj jako trzeci wybór z deeper coverage |
| `redeploy/pi109/diagnose.md` (8.5kB) | manualne checks fragmentów które op3 robi automatycznie (display, kernel, ports, services) |
| Examples z `op3` | `examples/` w op3 repo zawiera real-world `app.doql.less` z fraq, redeploy, doql |

## Companion tools

`op3` to klucz w pipeline:

```
sumd     → scan repo → SUMR.md (LLM snapshot)
op3      → scan device → snapshot.yaml (multi-layer state)
doql     → declare desired → app.doql.less + drift detection
redeploy → apply state → idempotent steps
```

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `op3: command not found` | `pip install --user --upgrade op3` |
| Scan zwraca `physical: null` | platform-specific probe — sprawdź `op3 scan host --layers physical -v` |
| `LessAdapter.parse` błąd | sprawdź `app.doql.less` syntax via `doql validate` |
| Bardzo długi scan | użyj `--layers <subset>` — full scan może trwać 30-60s na slow devices |
| Drift fałszywy positive | sprawdź `op3 diff --layer service` (zwykle drift jest na ports/endpoints) |

## Linki

- Repo / PyPI: https://pypi.org/project/op3/
- Wersja (2026-05-10): `op3==0.2.5`
- Built on: `fraq` (fractal data primitives)
- Companion: `doql` (declarative state), `redeploy` (apply state), `sumd` (LLM snapshot)
