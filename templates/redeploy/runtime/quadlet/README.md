# Quadlet templates (Podman rootless systemd)

Generic Quadlet (`*.container`, `*.network`) templates dla Podman rootless
deployment. Komplementarne do `templates/redeploy/device/` (markpact specs).

## Co dostajesz

| Plik | Rola |
|---|---|
| `app-backend.container.template` | Backend service Quadlet (port + healthcheck) |
| `app-frontend.container.template` | Frontend service Quadlet (depends-on backend) |
| `app.network.template` | Internal network dla service-to-service |

## Kiedy używać

Quadlet jest **prostą alternatywą** dla Docker Compose na Linux:

- **Rootless** (no daemon, no sudo)
- **systemd-native** (auto-start, restart, logs przez journalctl)
- **Cross-compilation friendly** (build x86_64, deploy ARM)

Idealne dla:

- Raspberry Pi deployment (rootless = bezpieczne)
- Long-running services bez Docker daemon
- Immutable infra (`systemctl --user daemon-reload`)

## Install

```bash
APP_NAME=myapp
APP_PORT=8000
FRONTEND_PORT=8100
VERSION=$(cat VERSION 2>/dev/null || echo 1.0.0)

mkdir -p quadlet
cp templates/redeploy/runtime/quadlet/app-backend.container.template     quadlet/${APP_NAME}-backend.container
cp templates/redeploy/runtime/quadlet/app-frontend.container.template    quadlet/${APP_NAME}-frontend.container
cp templates/redeploy/runtime/quadlet/app.network.template               quadlet/${APP_NAME}.network

# Substitute placeholders
find quadlet -type f | xargs sed -i \
  -e "s/<APP_NAME>/${APP_NAME}/g" \
  -e "s/<APP_PORT>/${APP_PORT}/g" \
  -e "s/<FRONTEND_PORT>/${FRONTEND_PORT}/g" \
  -e "s/<VERSION>/${VERSION}/g"

# Install na device (rootless):
ssh user@host "mkdir -p ~/.config/containers/systemd"
scp quadlet/* user@host:~/.config/containers/systemd/
ssh user@host "systemctl --user daemon-reload && \
               systemctl --user enable --now ${APP_NAME}-backend.service ${APP_NAME}-frontend.service"
```

## Integracja z `redeploy`

`templates/redeploy/device/migration.md.template` ma step
`install_quadlet`:

```yaml
- id: install_quadlet
  action: ssh_cmd
  command: |
    mkdir -p ~/.config/containers/systemd
    cp ~/<APP_NAME>/quadlet/*.container ~/.config/containers/systemd/
    cp ~/<APP_NAME>/quadlet/*.network   ~/.config/containers/systemd/
    systemctl --user daemon-reload
```

`doql quadlet` (companion w `doql`) potrafi wygenerować Quadlet z
`app.doql.less` declarative spec — alternatywa do tych templates.

## Customization

### Network mode `host` (RPi/embedded)

```ini
[Container]
Network=host
# (remove PublishPort lines)
```

### Multiple Volumes

```ini
[Container]
Volume=%h/<APP_NAME>/logs:/app/logs:Z
Volume=%h/<APP_NAME>/db:/app/db:Z,U
```

### Healthcheck custom command

```ini
[Container]
HealthCmd=/usr/local/bin/healthcheck.sh
HealthInterval=30s
HealthRetries=3
```

### Auto-update from registry

```ini
[Container]
AutoUpdate=registry
```

## Reference (c2004)

c2004 ma dwa zestawy quadlet:

- `c2004/quadlet/http/` — bez Traefik (dev/test)
- `c2004/quadlet/traefik/` — z Traefik reverse proxy (prod)

Plus pełny mapping doc: `redeploy/traefik-tar/MAPOWANIE.md`
(docker-compose ↔ Quadlet conversion guide).

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `systemd-run --user` permission | enable lingering: `loginctl enable-linger <user>` |
| Container nie startuje po `daemon-reload` | check: `journalctl --user -u <name>.service -n 50` |
| `Network not found` | install network FIRST: `systemctl --user start <APP_NAME>.network` |
| Healthcheck timeout | zwiększ `HealthStartPeriod=120s` dla slow-starting services |
| Image not found `localhost/<APP>` | build na device albo `podman load` z tarball |
