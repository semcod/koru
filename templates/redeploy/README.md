# redeploy templates

Templates dla `redeploy` (markpact-based deployment). Kopiowane do
docelowego repo przez `task template:install:redeploy` (kopiuje do
`./redeploy/`).

## Struktura

```text
templates/redeploy/
├── local/
│   └── deployment.md.template      # Local Docker Compose (dev)
└── device/
    ├── manifest.yaml.template      # Multi-phase orchestration
    ├── migration.md.template       # SSH+Podman/Docker deploy
    └── diagnose.md.template        # Read-only diagnostic
```

## Po skopiowaniu — placeholder substitution

Każdy template zawiera placeholdery typu `<APP_NAME>`, `<SSH_USER>@<SSH_HOST>`,
`<VERSION>`, `<RUNTIME>`. Po `task template:install:redeploy`:

```bash
# Quick replace via sed (CHANGE values for your setup):
APP_NAME=myapp
DEVICE=edge01
SSH=ubuntu@192.168.1.50
VERSION=1.0.0
RUNTIME=podman_quadlet      # or docker_compose

# Local
sed -i "s/<APP_NAME>/${APP_NAME}/g; s/<VERSION>/${VERSION}/g" \
  redeploy/local/deployment.md

# Device (rename device/ → <DEVICE>/ first)
mv redeploy/device redeploy/${DEVICE}
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

## Reference deployment

C2004 (`maskservice/c2004/redeploy/`) ma 7 strategii:

- `local/docker-compose/` — lokalny dev (Docker Compose)
- `pi109/` — RPi5 SSH + Podman Quadlet
- `podman-traefik/`, `traefik-tar/` — RPi5 produkcja
- `docker-compose/` — VPS produkcja
- `k3s/` — Kubernetes cluster
- `native/` — bez kontenerów

Każda strategia ma własny `manifest.yaml` + `migration.md` + `diagnose.md`.
Skopiuj odpowiednie templates jako baseline, dostosuj.

## Workflow

Pełny przewodnik: [`workflows/redeploy-multi-device.md`](../../workflows/redeploy-multi-device.md).
