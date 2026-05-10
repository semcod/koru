---
description: Multi-device deployment with redeploy + markpact specs
---

# redeploy multi-device deployment loop

Pattern wdrażania jednego repo do **wielu różnych targets** (localhost,
Raspberry Pi, VPS, K8s) z jednym tool-em (`redeploy`) i deklaratywnymi
spec-ami (`markpact` markdown).

```text
┌─────────────────────────────────────────────────────────────────┐
│                      Source repo (git)                          │
└────────┬────────────────┬─────────────────┬───────────────────┬─┘
         ▼                ▼                 ▼                   ▼
   ┌──────────┐    ┌──────────┐      ┌──────────┐       ┌──────────┐
   │ local/   │    │ pi109/   │      │ vps01/   │  ...  │ k3s/     │
   │ Docker   │    │ Podman   │      │ Compose  │       │ K8s      │
   │ Compose  │    │ Quadlet  │      │ + Traefik│       │          │
   └──────────┘    └──────────┘      └──────────┘       └──────────┘
        ▲                ▲                 ▲                   ▲
        └────── single tool: `redeploy run <spec>` ───────────┘
                            │
                  ┌─────────┴──────────┐
                  ▼                    ▼
           markpact spec        manifest.yaml
           (deployment.md)      (multi-phase)
```

Każdy target ma własny katalog `redeploy/<target>/` z spec-em (lub kilkoma
spec-ami i `manifest.yaml`).

## Filozofia

- **Spec to single source of truth** — `markpact:config` + `markpact:steps`
  + `markpact:ref` w jednym pliku Markdown. Nie ma `Dockerfile.dev` vs
  `Dockerfile.prod` oddzielnych skryptów Bash — wszystko w spec-u.
- **Idempotentne kroki** — `redeploy run` można uruchomić wiele razy bez
  efektów ubocznych. `--from-step` pozwala wznowić po awarii.
- **Plan / dry-run / apply** — zawsze możesz podejrzeć co się stanie
  przed faktyczną zmianą.
- **Drift detection przez `doql`** — `doql adopt --from-device` snapshot
  rzeczywistego stanu device → diff vs `app.doql.less` (intended state).

## Deployment checklist — wdrożenie w swoim repo

### Krok 1. Zainstaluj `redeploy`

```bash
bash docs/llm-tools/redeploy/install.sh
# lub ręcznie:
pip install --user --upgrade redeploy
```

Weryfikacja:

```bash
redeploy --version          # redeploy 0.2.74+
redeploy run --help | head  # markpact runner ready
```

### Krok 2. Skopiuj templates

```bash
task template:install:redeploy
# lub ręcznie:
mkdir -p redeploy/local redeploy/<DEVICE>
cp templates/redeploy/local/deployment.md.template     redeploy/local/deployment.md
cp templates/redeploy/device/manifest.yaml.template    redeploy/<DEVICE>/manifest.yaml
cp templates/redeploy/device/migration.md.template     redeploy/<DEVICE>/migration.md
cp templates/redeploy/device/diagnose.md.template      redeploy/<DEVICE>/diagnose.md
```

### Krok 3. Substituuj placeholdery

Każdy template ma placeholdery `<APP_NAME>`, `<DEVICE_NAME>`,
`<SSH_USER>@<SSH_HOST>`, `<VERSION>`, `<RUNTIME>`. Replace:

```bash
APP_NAME=myapp
DEVICE=edge01
SSH=ubuntu@192.168.1.50
VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")
RUNTIME=podman_quadlet           # albo docker_compose

# Local spec
sed -i "s/<APP_NAME>/${APP_NAME}/g; s/<VERSION>/${VERSION}/g" \
  redeploy/local/deployment.md

# Device spec — rename dir + sed
[ -d redeploy/device ] && mv redeploy/device redeploy/${DEVICE}
sed -i \
  -e "s/<APP_NAME>/${APP_NAME}/g" \
  -e "s/<DEVICE_NAME>/${DEVICE}/g" \
  -e "s|<SSH_USER>@<SSH_HOST>|${SSH}|g" \
  -e "s/<SSH_USER>/${SSH%@*}/g" \
  -e "s/<SSH_HOST>/${SSH#*@}/g" \
  -e "s/<VERSION>/${VERSION}/g" \
  -e "s/<RUNTIME>/${RUNTIME}/g" \
  redeploy/${DEVICE}/*.md redeploy/${DEVICE}/*.yaml
```

### Krok 4. Dostosuj porty + ścieżki

Każdy spec ma:

- **Ports** w `markpact:ref` skryptach (kill-dev, smoke-test) — domyślnie
  `8000`/`8100`. Edit dla swoich serwisów.
- **`remote_dir`** w `markpact:config` — domyślnie `~/<APP_NAME>`. Edit
  jeśli chcesz `/opt/<APP_NAME>` albo coś innego.
- **`verify_url`** + `health_checks` — endpoint health twojego backendu.
- **`build-frontend` / `build-backend`** w `migration.md` — Dockerfile
  paths. Edit jeśli masz inną strukturę (`backend/Dockerfile`,
  `frontend/Dockerfile.prod`, etc.).

### Krok 5. Zainstaluj `quality:deploy:*` taski w Taskfile

Skopiuj z `Taskfile.yml` (sekcja "Deploy"):

```yaml
deploy:plan:
  desc: 'Plan deploy (no changes) — DEVICE=<name> (default: local)'
  cmds:
    - redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --plan-only

deploy:dry:
  desc: 'Dry run deploy — DEVICE=<name> (default: local)'
  cmds:
    - redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --dry-run

deploy:local:
  desc: Deploy locally (Docker Compose)
  cmds:
    - redeploy run redeploy/local/deployment.md

deploy:device:
  desc: 'Deploy to device — DEVICE=<name> (e.g. pi109, edge01)'
  cmds:
    - redeploy run "redeploy/{{.DEVICE}}/migration.md"
  requires:
    vars: [DEVICE]

deploy:diagnose:
  desc: 'Read-only diagnose — DEVICE=<name>'
  cmds:
    - redeploy run "redeploy/{{.DEVICE | default \"local\"}}/diagnose.md"

deploy:resume:
  desc: 'Resume deploy — DEVICE=<name> STEP=<id>'
  cmds:
    - redeploy run "redeploy/{{.DEVICE}}/migration.md" --from-step {{.STEP}}
  requires:
    vars: [DEVICE, STEP]
```

### Krok 6. Pierwszy deploy (lokalnie, bezpiecznie)

```bash
# Plan only — zobacz co się stanie
task deploy:plan
# albo: redeploy run redeploy/local/deployment.md --plan-only

# Dry run — wykonaj bez efektów
task deploy:dry

# Pełny deploy
task deploy:local
```

### Krok 7. Pierwszy deploy na device (SSH)

```bash
# Wymagane: ssh-copy-id <SSH_USER>@<SSH_HOST> przed pierwszym uruchomieniem

task deploy:plan DEVICE=edge01
task deploy:dry DEVICE=edge01
task deploy:device DEVICE=edge01
```

### Krok 8. Snapshot intended state (drift baseline)

Po pierwszym udanym deploy:

```bash
# Wymaga: doql installed
doql adopt --from-device <SSH_USER>@<SSH_HOST> -o app.doql.less
git add app.doql.less
git commit -m "chore(deploy): snapshot intended state for <DEVICE>"
```

`app.doql.less` to **single source of truth** dla rzeczywistego stanu
device — następne deploye będą porównywać manifest vs realne usługi i
pause-ować przy drift.

### Krok 9. Weryfikacja end-to-end

```bash
# Local
test -f redeploy/local/deployment.md && echo "OK: local spec exists"
redeploy run redeploy/local/deployment.md --plan-only >/dev/null && echo "OK: local spec valid"

# Device
test -f redeploy/<DEVICE>/manifest.yaml && echo "OK: <DEVICE> manifest exists"
test -f redeploy/<DEVICE>/migration.md && echo "OK: <DEVICE> migration spec exists"
test -f redeploy/<DEVICE>/diagnose.md && echo "OK: <DEVICE> diagnose spec exists"
redeploy run redeploy/<DEVICE>/migration.md --plan-only >/dev/null && echo "OK: <DEVICE> migration spec valid"

# Health checks (after first deploy)
curl -fsS http://localhost:8000/health && echo "OK: backend healthy"
test -s app.doql.less && echo "OK: intended state captured"
```

## Multi-device — typowe topologie

### Lokalny dev + jeden device produkcyjny

```text
redeploy/
├── local/deployment.md        # codzienny dev
└── pi109/
    ├── manifest.yaml          # multi-phase
    ├── migration.md           # production deploy
    └── diagnose.md            # read-only

# Workflow:
task deploy:local                    # dev po każdej zmianie
task deploy:device DEVICE=pi109      # weekly produkcja
```

### Wiele devices z tej samej strategii

```text
redeploy/
├── local/deployment.md
├── edge01/migration.md        # różny SSH_HOST
├── edge02/migration.md        # różny SSH_HOST
└── edge03/migration.md
```

Każdy `migration.md` różni się tylko `<SSH_HOST>` w `markpact:config`.

```bash
for dev in edge01 edge02 edge03; do
  task deploy:device DEVICE=$dev
done
```

### Wiele strategii (jak c2004)

```text
redeploy/
├── local/docker-compose/deployment.md     # dev
├── pi109/migration.md                     # RPi5 (Podman+Traefik)
├── traefik-tar/deployment.yaml           # RPi5 (Nginx, prostsze)
├── docker-compose/deployment.yaml        # VPS produkcja
└── k3s/deployment.yaml                    # K8s cluster
```

Każda ma inną `strategy:` w `markpact:config` i inne `markpact:ref` skrypty
budowy. Wybierasz ad-hoc:

```bash
redeploy run redeploy/k3s/deployment.yaml --device prod-cluster
```

## Multi-phase deploy z manifest.yaml

Dla kompleksowych deployments z `hardware-init` + `deploy` + `diagnose` +
`fix-*`:

```bash
# Sekwencyjnie (do czasu gdy `redeploy run --manifest` doczeka v1):
for phase in hardware-init migration; do
  redeploy run "redeploy/<DEVICE>/${phase}.md"
done

# Diagnoza po deploy
redeploy run redeploy/<DEVICE>/diagnose.md

# Fix on-demand (gdy widać symptom)
redeploy run redeploy/<DEVICE>/fix-kiosk.md
```

## Drift loop

```text
┌─────────────────────────────────────────────────────────┐
│  1. redeploy run <DEVICE>/migration.md                  │
│     ↓ deploy passes                                     │
│  2. doql adopt --from-device <SSH_USER>@<SSH_HOST>      │
│     ↓ snapshot                                          │
│  3. git diff app.doql.less                              │
│     ├─ no diff   → commit & push                        │
│     └─ has diff  → review (someone changed device       │
│                    state outside redeploy)              │
│  4. Next time: redeploy run notices drift, pauses       │
│     and asks before applying                            │
└─────────────────────────────────────────────────────────┘
```

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `Permission denied (publickey)` | `ssh-copy-id <SSH_USER>@<SSH_HOST>` przed pierwszym deploy |
| `markpact spec invalid` | sprawdź fenced block syntax: `bash markpact:ref name`, nie `bash markpact-ref` |
| Step zawisa po SSH command | `pkill -f` zabija sshd. Use `pkill -x` lub `systemd-run --user --collect` |
| Background `&` w `ssh_cmd` → exit=255 | `&` w SSH context działa źle. Use `systemd-run --user --collect` |
| `port already in use` | dodaj step `kill_dev_processes` z plugin `process_control` lub script `stop-dev-services` |
| Drift między manifest a device | `doql adopt --from-device` → review → commit nowy `app.doql.less` |
| `--from-step` skip-uje step który chciałeś | sprawdź `id:` w `markpact:steps` — case-sensitive |

## Odroll / disable

```bash
# Stop services on device (safe rollback step)
ssh <SSH_USER>@<SSH_HOST> 'systemctl --user stop "<APP_NAME>-*.service"'

# Remove templates from repo
rm -rf redeploy/

# Remove pip package
pip uninstall redeploy
```

## Reference deployment

Templates pochodzą z [`maskservice/c2004/redeploy/`](https://github.com/maskservice/c2004/tree/main/redeploy)
(produkcja, 7 strategii). Tam możesz zobaczyć:

- `local/deployment.md` — pełny markpact dla Docker Compose dev
- `pi109/manifest.yaml` — multi-phase RPi5 deployment z hardware-init,
  fix-kiosk, fix-hardware
- `pi109/migration.md` — Podman Quadlet rootless (~680 linii spec-u)
- `pi109/diagnose.md` — read-only diagnostic z 8 fazami
- `traefik-tar/MAPOWANIE.md` — szczegółowe mapowanie docker-compose →
  Podman Quadlet (cross-compilation insights)
