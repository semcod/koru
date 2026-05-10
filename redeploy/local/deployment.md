# <APP_NAME> Local Docker Compose Deployment — Declarative Spec

Markpact spec for local Docker Compose deployment. Substitute placeholders
(`<APP_NAME>`, `<VERSION>`, ports) before first run.

## How to run

```bash
cd /path/to/your/repo

redeploy run redeploy/local/deployment.md --plan-only   # podgląd kroków
redeploy run redeploy/local/deployment.md --dry-run     # suchy przebieg
redeploy run redeploy/local/deployment.md               # pełny deploy
redeploy run redeploy/local/deployment.md --from-step start_services  # wznowienie
```

## Declarative configuration

```yaml markpact:config
name: "<APP_NAME> local docker-compose deploy <VERSION>"
description: "Deploy <APP_NAME> locally via Docker Compose with declarative testing"

source:
  strategy: docker_full
  host: localhost
  app: <APP_NAME>
  version: "<VERSION>"
  remote_dir: /path/to/your/repo

target:
  strategy: docker_full
  host: localhost
  app: <APP_NAME>
  version: "<VERSION>"
  remote_dir: /path/to/your/repo
  env_file: /path/to/your/repo/.env
  verify_url: http://localhost:8000/health
  verify_version: "v1"

notes:
  - "Local Docker Compose deployment WITHOUT reverse proxy"
  - "Direct port mapping: frontend:8100, backend:8000"
  - "Uses docker-compose.yml + docker-compose.dev.yml (if exists)"
  - "Auto-kills dev processes on configured ports before deployment"
```

## Reusable scripts

### Update env version from VERSION file

```bash markpact:ref update-env-version
#!/bin/bash
set -euo pipefail
REPO=/path/to/your/repo
VERSION=$(cat "$REPO/VERSION" 2>/dev/null | tr -d '[:space:]')
[ -z "$VERSION" ] && { echo 'FAIL: brak VERSION'; exit 1; }
sed -i "s/^SERVICE_VERSION=.*/SERVICE_VERSION=$VERSION/" "$REPO/.env"
echo "PASS: .env zaktualizowany do $VERSION"
```

### HTTP endpoint test

```bash markpact:ref http-endpoint-test
#!/bin/bash
# Usage: http-endpoint-test URL EXPECTED_STATUS TIMEOUT
set -euo pipefail
URL="${1:-http://localhost:8000/health}"
EXPECTED_STATUS="${2:-200}"
TIMEOUT="${3:-5}"
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" "$URL" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "$EXPECTED_STATUS" ] && echo "OK: HTTP $HTTP_CODE ($URL)" || \
  { echo "FAIL: HTTP $HTTP_CODE (expected $EXPECTED_STATUS, $URL)"; exit 1; }
```

### Stop dev services (reusable port-manager logic)

```bash markpact:ref stop-dev-services
#!/bin/bash
set -euo pipefail
REPO=/path/to/your/repo
cd "$REPO"

echo "[1] docker compose down (remove orphans)"
docker compose down --remove-orphans 2>/dev/null || true

echo "[2] kill processes on project ports"
for port in 8000 8100; do  # CHANGE: list your service ports
  PIDS=$(lsof -ti:"$port" 2>/dev/null || true)
  for pid in $PIDS; do
    kill -TERM "$pid" 2>/dev/null || true
  done
done
sleep 2
for port in 8000 8100; do
  PIDS=$(lsof -ti:"$port" 2>/dev/null || true)
  for pid in $PIDS; do
    kill -9 "$pid" 2>/dev/null || true
  done
done

echo "PASS: dev services stopped, ports free"
```

### Smoke test all services

```bash markpact:ref smoke-test
#!/bin/bash
set -euo pipefail
REPO=/path/to/your/repo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SMOKE TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Containers up?
docker compose -f "$REPO/docker-compose.yml" ps --format json | \
  python3 -c "import sys, json; \
[print(f\"{x['Service']}: {x['State']}\") for x in (json.loads(l) for l in sys.stdin if l.strip())]" || true

# HTTP endpoints
for u in http://localhost:8000/health http://localhost:8100/; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$u" || echo 000)
  echo "  $CODE  $u"
done
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Migration steps

```yaml markpact:steps
extra_steps:
  - id: sync_env
    action: inline_script
    description: "Skip sync_env for localhost (source=target)"
    command: echo "Skipping sync_env - localhost deployment"
    risk: low

  - id: update_env_version
    action: inline_script
    description: "Aktualizuj SERVICE_VERSION w .env z VERSION"
    command_ref: update-env-version
    insert_before: docker_build_pull

  - id: kill_dev_processes
    action: inline_script
    description: "Stop docker containers + kill port processes"
    command_ref: stop-dev-services
    risk: low
    insert_before: docker_build_pull

  - id: docker_build_pull
    action: inline_script
    description: "Build/pull Docker images"
    command: docker compose -f /path/to/your/repo/docker-compose.yml build
    risk: medium

  - id: start_services
    action: inline_script
    description: "Start services"
    command: docker compose -f /path/to/your/repo/docker-compose.yml up -d
    risk: medium

  - id: hardware_diagnostic
    action: plugin
    plugin_type: hardware_diagnostic
    description: "Analyze system hardware (platform/cpu/memory/storage)"
    plugin_params:
      checks: ["platform", "cpu", "memory", "storage"]
      platform: auto
    risk: low

  - id: http_health_check
    action: http_check
    description: "Verify backend health endpoint"
    url: http://localhost:8000/health
    expect: healthy
    risk: low

  - id: smoke_test
    action: inline_script
    description: "Run comprehensive smoke test"
    command_ref: smoke-test
    risk: low

  - id: show_urls
    action: inline_script
    description: "Show access URLs"
    command: >
      echo "" &&
      echo "🚀 Services started:" &&
      echo "   Frontend: http://localhost:8100" &&
      echo "   Backend:  http://localhost:8000" &&
      echo ""
    risk: low
```

## Post-deployment verification

```bash
# Containers
docker compose ps

# Logs
docker compose logs -f --tail=50

# Manual smoke test
redeploy exec 'smoke-test' --file redeploy/local/deployment.md
```
