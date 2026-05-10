# <APP_NAME> @ <DEVICE_NAME> — Diagnose (read-only)

Read-only infrastructure snapshot — safe to run any time.

Substitute placeholders before first run.

## Run

```bash
redeploy run redeploy/<DEVICE_NAME>/diagnose.md           # full diagnostic
redeploy run redeploy/<DEVICE_NAME>/diagnose.md --plan-only  # show only what would be checked
```

## Markpact config

```yaml markpact:config
name: "<APP_NAME> diagnose <DEVICE_NAME>"
description: "Read-only infrastructure snapshot"

source:
  strategy: diagnostic
  host: localhost
  app: <APP_NAME>

target:
  host: <SSH_USER>@<SSH_HOST>
  app: <APP_NAME>

notes:
  - "Wszystkie kroki są read-only — nic nie zmieniają na device"
  - "Bezpieczne uruchamiać równolegle z innymi operacjami"
```

## Diagnostic scripts

```bash markpact:ref check-services
#!/bin/bash
echo "━━━ Systemd user services ━━━"
systemctl --user list-units --type=service "<APP_NAME>-*" --no-pager 2>/dev/null \
  || echo "  (no <APP_NAME>-*.service units found)"
echo ""
echo "━━━ Failed services (system-wide) ━━━"
systemctl --user --failed --no-pager 2>/dev/null | head -20
```

```bash markpact:ref check-containers
#!/bin/bash
echo "━━━ Podman containers (rootless) ━━━"
podman ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" 2>/dev/null \
  || echo "  podman not available"
echo ""
echo "━━━ Docker containers (root) ━━━"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" 2>/dev/null \
  || echo "  docker not available"
```

```bash markpact:ref check-ports
#!/bin/bash
echo "━━━ Listening ports ━━━"
ss -tlnp 2>/dev/null | head -30 \
  || netstat -tlnp 2>/dev/null | head -30 \
  || echo "  ss/netstat not available"
```

```bash markpact:ref check-endpoints
#!/bin/bash
echo "━━━ HTTP endpoints ━━━"
for u in "http://localhost:8000/health" "http://localhost:8100/"; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$u" || echo 000)
  echo "  $CODE  $u"
done
```

```bash markpact:ref check-resources
#!/bin/bash
echo "━━━ Disk usage ━━━"
df -h | head -10
echo ""
echo "━━━ Memory ━━━"
free -h
echo ""
echo "━━━ CPU/load ━━━"
uptime
```

```bash markpact:ref check-logs-tail
#!/bin/bash
echo "━━━ <APP_NAME> service logs (last 30 lines) ━━━"
for svc in <APP_NAME>-backend <APP_NAME>-frontend; do
  echo "── $svc.service ──"
  journalctl --user -u "${svc}.service" -n 30 --no-pager 2>/dev/null \
    || echo "  (no logs available)"
done
```

## Diagnostic steps

```yaml markpact:steps
extra_steps:
  - id: ssh_reachable
    action: ssh_cmd
    description: "SSH reachability + uname"
    command: uname -a && hostnamectl 2>/dev/null | head -10
    risk: low

  - id: services_status
    action: ssh_cmd
    description: "Systemd services status"
    command_ref: check-services
    risk: low

  - id: containers_status
    action: ssh_cmd
    description: "Container runtime status (podman/docker)"
    command_ref: check-containers
    risk: low

  - id: listening_ports
    action: ssh_cmd
    description: "Listening ports"
    command_ref: check-ports
    risk: low

  - id: http_endpoints
    action: ssh_cmd
    description: "HTTP endpoint reachability"
    command_ref: check-endpoints
    risk: low

  - id: system_resources
    action: ssh_cmd
    description: "Disk/memory/CPU"
    command_ref: check-resources
    risk: low

  - id: recent_logs
    action: ssh_cmd
    description: "<APP_NAME> service logs (last 30 lines)"
    command_ref: check-logs-tail
    risk: low

  - id: drift_check
    action: ssh_cmd
    description: "Quick drift check (intended state vs actual)"
    command: |
      if [ -f ~/<APP_NAME>/app.doql.less ]; then
        echo "Intended state file present: ~/<APP_NAME>/app.doql.less"
        wc -l ~/<APP_NAME>/app.doql.less
      else
        echo "WARN: brak ~/<APP_NAME>/app.doql.less — uruchom 'doql adopt' lokalnie i scp"
      fi
    risk: low
```

## Manual follow-ups

Po diagnostyce, jeśli widzisz problemy:

```bash
# Service down / unhealthy → restart
ssh <SSH_USER>@<SSH_HOST> 'systemctl --user restart <APP_NAME>-backend.service'

# Drift between manifest and reality → refresh intended state
doql adopt --from-device <SSH_USER>@<SSH_HOST> -o app.doql.less

# Full redeploy
redeploy run redeploy/<DEVICE_NAME>/migration.md
```
