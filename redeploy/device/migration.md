# <APP_NAME> @ <DEVICE_NAME> — Core Deploy

Markpact spec for SSH-based deployment to a device.

Substitute placeholders (`<APP_NAME>`, `<SSH_USER>@<SSH_HOST>`, `<VERSION>`,
`<RUNTIME>`) before first run.

## Run

```bash
cd /path/to/your/repo

redeploy run redeploy/<DEVICE_NAME>/migration.md --plan-only   # plan
redeploy run redeploy/<DEVICE_NAME>/migration.md --dry-run     # preview
redeploy run redeploy/<DEVICE_NAME>/migration.md               # full
redeploy run redeploy/<DEVICE_NAME>/migration.md --from-step assert-backend-healthy
```

## Operational notes

- `pkill -f` zabija sshd — używaj `pkill -x` (exact match)
- Background `&` w `ssh_cmd` → exit=255; użyj `systemd-run --user --collect`
- Wieloliniowe SSH commands: `command: |` (nie `>`)
- Podman rootless = `~/.config/containers/systemd/` dla Quadlet
- Docker daemon root = `/etc/docker/...` lub `~/.docker/...`
- Runtime logi nie są synchronizowane (dodaj do `.redeployignore`)

## Markpact config

```yaml markpact:config
name: "<APP_NAME> deploy <DEVICE_NAME> <VERSION>"
description: "Deploy <APP_NAME> to <DEVICE_NAME> via SSH + <RUNTIME>"

source:
  strategy: <RUNTIME>
  host: localhost
  app: <APP_NAME>
  version: "<VERSION>"
  remote_dir: /path/to/your/repo

target:
  strategy: <RUNTIME>
  host: <SSH_USER>@<SSH_HOST>
  app: <APP_NAME>
  version: "<VERSION>"
  remote_dir: "~/<APP_NAME>"
  env_file: "~/<APP_NAME>/.env"
  verify_url: http://<SSH_HOST>:8000/health
  verify_version: "v1"

notes:
  - "Build images locally, scp to device, install Quadlet/Compose units"
  - "Rootless podman by default; switch to root for system services"
```

## Reusable scripts

```bash markpact:ref update-env-version
#!/bin/bash
set -euo pipefail
VERSION=$(cat ~/<APP_NAME>/VERSION 2>/dev/null | tr -d '[:space:]')
[ -z "$VERSION" ] && { echo 'FAIL: brak VERSION'; exit 1; }
sed -i "s/^SERVICE_VERSION=.*/SERVICE_VERSION=$VERSION/" ~/<APP_NAME>/.env
echo "PASS: .env zaktualizowany do $VERSION"
```

```bash markpact:ref build-backend
#!/bin/bash
set -euo pipefail
VERSION=$(grep '^SERVICE_VERSION=' ~/<APP_NAME>/.env | cut -d= -f2)
cd ~/<APP_NAME>
podman build \
  -t localhost/<APP_NAME>-backend:${VERSION} \
  -t localhost/<APP_NAME>-backend:latest \
  -f backend/Dockerfile . &&
echo "PASS: <APP_NAME>-backend:${VERSION} zbudowany"
```

```bash markpact:ref build-frontend
#!/bin/bash
set -euo pipefail
VERSION=$(grep '^SERVICE_VERSION=' ~/<APP_NAME>/.env | cut -d= -f2)
cd ~/<APP_NAME>
podman build \
  --build-arg PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
  --build-arg VITE_SERVICE_VERSION=${VERSION} \
  -t localhost/<APP_NAME>-frontend:${VERSION} \
  -t localhost/<APP_NAME>-frontend:latest \
  -f frontend/Dockerfile . &&
echo "PASS: <APP_NAME>-frontend:${VERSION} zbudowany"
```

```bash markpact:ref restart-service
#!/bin/bash
# Stop, remove container, start to ensure latest image is used
SVC="${1:-<APP_NAME>-backend}"
systemctl --user stop "${SVC}.service" 2>/dev/null || true
sleep 2
podman rm -f "$SVC" 2>/dev/null || true
sleep 1
systemctl --user start "${SVC}.service"
sleep 3
systemctl --user is-active "${SVC}.service"
echo "PASS: $SVC zrestartowany"
```

```bash markpact:ref smoke-test
#!/bin/bash
set -euo pipefail
echo "━━━ <APP_NAME> @ <DEVICE_NAME> smoke test ━━━"
for u in "http://<SSH_HOST>:8000/health" "http://<SSH_HOST>:8100/"; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$u" || echo 000)
  echo "  $CODE  $u"
done
systemctl --user list-units --type=service "<APP_NAME>-*" --no-pager 2>/dev/null || true
```

## Migration steps

```yaml markpact:steps
extra_steps:
  - id: sync_env
    action: rsync
    description: "Sync source repo to device (~/<APP_NAME>/)"
    source: /path/to/your/repo/
    target: "~/<APP_NAME>/"
    exclude_file: redeploy/<DEVICE_NAME>/.redeployignore
    risk: low

  - id: update_env_version
    action: ssh_cmd
    description: "Aktualizuj SERVICE_VERSION w .env z VERSION"
    command_ref: update-env-version
    risk: low
    insert_after: sync_env

  - id: build_backend
    action: ssh_cmd
    description: "Build backend image"
    command_ref: build-backend
    risk: medium
    insert_after: update_env_version

  - id: build_frontend
    action: ssh_cmd
    description: "Build frontend image"
    command_ref: build-frontend
    risk: medium
    insert_after: build_backend

  - id: install_quadlet
    action: ssh_cmd
    description: "Install Podman Quadlet units (rootless)"
    command: |
      mkdir -p ~/.config/containers/systemd
      cp ~/<APP_NAME>/quadlet/*.container ~/.config/containers/systemd/
      cp ~/<APP_NAME>/quadlet/*.network   ~/.config/containers/systemd/ 2>/dev/null || true
      systemctl --user daemon-reload
      echo "PASS: Quadlet units installed"
    risk: medium
    insert_after: build_frontend

  - id: start_services
    action: ssh_cmd
    description: "Start <APP_NAME> services (rootless systemd)"
    command: |
      systemctl --user start <APP_NAME>-backend.service
      systemctl --user start <APP_NAME>-frontend.service
      sleep 5
      systemctl --user is-active <APP_NAME>-backend.service
      systemctl --user is-active <APP_NAME>-frontend.service
    risk: medium
    insert_after: install_quadlet

  - id: assert_backend_healthy
    action: http_check
    description: "Backend health endpoint"
    url: http://<SSH_HOST>:8000/health
    expect: healthy
    timeout: 30
    risk: low

  - id: assert_frontend_healthy
    action: http_check
    description: "Frontend reachable"
    url: http://<SSH_HOST>:8100/
    expect_status: 200
    timeout: 10
    risk: low

  - id: smoke_test
    action: ssh_cmd
    description: "Comprehensive smoke test"
    command_ref: smoke-test
    risk: low

  - id: show_urls
    action: ssh_cmd
    description: "Show access URLs"
    command: |
      echo ""
      echo "🚀 <APP_NAME> @ <DEVICE_NAME> deployed:"
      echo "   Frontend: http://<SSH_HOST>:8100"
      echo "   Backend:  http://<SSH_HOST>:8000"
      echo ""
      echo "📝 Logs:    journalctl --user -u <APP_NAME>-backend.service -f"
      echo "🛑 Stop:    systemctl --user stop '<APP_NAME>-*.service'"
    risk: low
```

## Post-deployment verification

```bash
# Service status
ssh <SSH_USER>@<SSH_HOST> 'systemctl --user list-units --type=service "<APP_NAME>-*" --no-pager'

# Logs (last 50 lines)
ssh <SSH_USER>@<SSH_HOST> 'journalctl --user -u <APP_NAME>-backend.service -n 50 --no-pager'

# Run smoke test manually
redeploy exec 'smoke-test' --file redeploy/<DEVICE_NAME>/migration.md

# Refresh intended state (drift baseline)
doql adopt --from-device <SSH_USER>@<SSH_HOST> -o app.doql.less
```
