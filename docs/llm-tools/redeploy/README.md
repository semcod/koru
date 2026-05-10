# redeploy — multi-target deployment automation

## Co to jest

`redeploy` (PyPI: `redeploy>=0.2.74`) to **infrastructure migration toolkit**
oparty o pattern: **detect → plan → apply** z deklaratywnymi spec-ami.

Spec to **markpact** — plik Markdown (`*.md`) lub czysty YAML zawierający:

- `markpact:config` — gdzie deploy (host, strategia, wersja, zdrowie)
- `markpact:steps` — co wykonać (idempotentne kroki: SSH, scripts, plugins)
- `markpact:ref` — reusable code blocks (skrypty bash z markdown)

Plus opcjonalny `manifest.yaml` orkiestrujący wiele faz dla jednego
urządzenia (`hardware-init` → `deploy` → `diagnose` → `fix-*`).

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Deploy lokalny (Docker Compose) | `redeploy run redeploy/local/deployment.md` |
| Deploy zdalny (SSH + Podman/Docker) | `redeploy run redeploy/<device>/migration.md` |
| Plan-only (podgląd) | `redeploy run <spec> --plan-only` |
| Dry run (preview changes) | `redeploy run <spec> --dry-run` |
| Wznowienie od kroku | `redeploy run <spec> --from-step <id>` |
| Diagnostyka (read-only) | `redeploy run redeploy/<device>/diagnose.md` |
| Drift detection | `doql adopt --from-device user@host` (companion) |

## Konfiguracja

### Brak osobnego configu

Cała konfiguracja w specu (`*.md` z `markpact:config`). Każdy device ma
własny katalog `redeploy/<device>/`:

```
redeploy/
├── local/                       # localhost
│   └── deployment.md            # markpact spec
├── pi109/                       # SSH device
│   ├── manifest.yaml            # multi-phase orchestration
│   ├── migration.md             # full deploy spec
│   ├── diagnose.md              # read-only diagnostic
│   ├── fix-kiosk.md             # on-demand fix
│   └── hardware.yaml            # hardware profile
└── README.md                    # device → strategy mapping
```

### Env vars

| Env var | Cel |
|---|---|
| `REDEPLOY_VERBOSE=1` | szczegółowe logi |
| `SSH_KEY=~/.ssh/id_rsa` | dla SSH-based deployments (paramiko) |

## Komendy

```bash
# Show help + version
redeploy --help
redeploy --version

# Plan only (no changes)
redeploy run redeploy/local/deployment.md --plan-only

# Dry run (preview commands)
redeploy run redeploy/local/deployment.md --dry-run

# Full deployment
redeploy run redeploy/pi109/migration.md

# Resume from specific step
redeploy run redeploy/pi109/migration.md --from-step assert-backend-healthy

# Execute single ref block from spec (debugging)
redeploy exec 'c2004-smoke-test' --file redeploy/local/deployment.md

# Detect intended state (companion: doql)
doql adopt --from-device user@host -o app.doql.less
```

## Integracja z koru

Koru dostarcza:

| Plik | Rola |
|---|---|
| [`templates/redeploy/local/deployment.md.template`](../../../templates/redeploy/local/deployment.md.template) | Local Docker Compose deployment (dev) |
| [`templates/redeploy/device/manifest.yaml.template`](../../../templates/redeploy/device/manifest.yaml.template) | Multi-phase SSH device orchestration |
| [`templates/redeploy/device/migration.md.template`](../../../templates/redeploy/device/migration.md.template) | Markpact spec dla SSH+Podman/Docker |
| [`templates/redeploy/device/diagnose.md.template`](../../../templates/redeploy/device/diagnose.md.template) | Read-only diagnostic (status, logs, ports) |
| Workflow | [`workflows/redeploy-multi-device.md`](../../../workflows/redeploy-multi-device.md) |

Pełny workflow: copy templates → customize hosts/version/health
checks → `task deploy:local` lub `task deploy:device DEVICE=pi109`.

## Reference deployment (c2004)

Produkcyjny deployment w `maskservice/c2004` — 7+ device strategii:

| Strategia | Target | Reverse Proxy | Use Case |
|---|---|---|---|
| `local/docker-compose` | localhost | none | dev / lokalne testy |
| `pi109/` | RPi5 (192.168.188.109) | Traefik / Nginx | produkcja embedded |
| `podman-traefik/` | RPi5 | Traefik v3.6 (rootless) | produkcja Pi z TLS |
| `traefik-tar/` | RPi5 | Nginx reverse proxy | produkcja Pi (cross-compile) |
| `docker-compose/` | VPS | Traefik | VPS produkcyjny |
| `k3s/` | cluster | nginx-ingress | Kubernetes |
| `native/` | bare PC | brak | dev bez kontenerów |

Każda strategia ma:

- `deployment.md` lub `manifest.yaml` (markpact spec / orkiestracja)
- `README.md` (per-strategy troubleshooting)
- `.redeployignore` (rsync exclusions, jeśli używa scp/rsync)

## Plugin system

`redeploy` wspiera pluginy (`action: plugin` w stepie):

| Plugin | Cel |
|---|---|
| `hardware_diagnostic` | scan platformy (CPU/RAM/storage/GPIO/USB/audio) |
| `process_control` | kill processes na portach (graceful → SIGKILL) |
| `http_check` | endpoint health (`url`, `expect_status`, `timeout`) |
| `version_check` | zgodność wersji deployed vs intended |
| `container_check` | docker/podman container running + healthy |

Plus własne markpact `inline_script` lub `ssh_cmd` actions dla
szczegółowych operacji.

## Workflow phases (manifest.yaml)

Manifest urządzenia definiuje **fazy lifecycle**:

```yaml
phases:
  - name: hardware-init      # Phase 0: one-time, may reboot
    when: first_deploy
  - name: deploy             # Phase 1: build + push + start
    when: always
  - name: diagnose           # Phase 2: read-only snapshot
    when: always
  - name: detect             # Phase 3: doql adopt → app.doql.less
    when: post_deploy
  - name: fix-kiosk          # Phase N: on-demand
    when: on_demand
    triggers:
      - symptom: kiosk_not_displaying
        detect: "ssh user@host 'pgrep chromium || echo MISSING'"
```

Każda faza ma `preconditions`/`postconditions` (commands lub `health_check`
references). Drift detection przez `doql adopt`.

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `redeploy: command not found` | `pip install --user redeploy` |
| `Permission denied (publickey)` | `ssh-copy-id user@host` lub `--ssh-key /path/to/key` |
| `markpact spec invalid` | sprawdź fenced block syntax (`bash markpact:ref name`) |
| Step zawisa po SSH command | `pkill -f` zabija sshd — używaj `pkill -x` (exact) lub `systemd-run --user --collect` |
| Background `&` w ssh_cmd → exit=255 | `&` w SSH context działa źle; użyj `systemd-run --user --collect` |
| `port already in use` przed deploymentem | dodaj `kill_dev_processes` step z plugin `process_control` |
| Drift: manifest mówi A, device ma B | `doql adopt --from-device` → commit → kolejny `redeploy run` |

## Linki

- Repo / PyPI: https://pypi.org/project/redeploy/
- Wersja (2026-05-10): `redeploy==0.2.74`
- Deps: `paramiko` (SSH), `httpx` (HTTP checks), `pydantic` (config), `markdown-it-py` (markpact parser)
- Reference deployment: [`maskservice/c2004/redeploy/`](https://github.com/maskservice/c2004/tree/main/redeploy) — 7 strategii + 2 zasięgi (local + RPi5)
- Companion: `doql` (drift detection — porównuje spec vs device state)
