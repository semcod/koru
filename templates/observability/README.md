# observability templates

Real-time monitoring + self-healing stack templates. Bazują na c2004
production deployment.

## Co dostajesz

10 services in one Docker Compose stack:

| Service | Port | Rola |
|---|---|---|
| **prometheus** | 9090 | metrics scraper + alert rules |
| **alertmanager** | 9093 | route alerts → healing-webhook |
| **grafana** | 3000 | dashboards (anonymous viewer default) |
| **loki** | 3100 | log aggregation |
| **promtail** | 9080 | ship container logs → loki |
| **blackbox-exporter** | 9115 | synthetic HTTP probes |
| **node-exporter** | 9100 | host metrics (CPU/RAM/disk) |
| **cadvisor** | 8082 | container metrics |
| **uptime-kuma** | 3001 | simple uptime UI |
| **healing-webhook** | 8810 | alert → planfile ticket / redsl improve |

## Struktura templates

```text
templates/observability/
├── docker-compose.observability.yml.template
├── prometheus/
│   ├── prometheus.yml.template
│   └── rules/
│       └── app-alerts.yml.template
├── alertmanager/
│   └── alertmanager.yml.template
└── grafana/
    └── provisioning/   (puste — dodaj swoje dashboards)
```

## Po skopiowaniu — substitute placeholders

Każdy template ma placeholdery `<APP_NAME>`, `<APP_PORT>`, `<APP_HOST>`.

```bash
# Z docelowego repo:
APP_NAME=myapp
APP_PORT=8000

# Skopiuj templates
task template:install:observability      # albo ręcznie wg sekcji "Manual install"

# Substitute:
find monitoring/ docker-compose.observability.yml -type f \( -name '*.yml' -o -name '*.template' \) | \
  xargs sed -i \
    -e "s/<APP_NAME>/${APP_NAME}/g" \
    -e "s/<APP_PORT>/${APP_PORT}/g"

# Rename .template files:
find monitoring/ -name '*.template' | while read f; do mv "$f" "${f%.template}"; done
mv docker-compose.observability.yml.template docker-compose.observability.yml
```

## Manual install

```bash
mkdir -p monitoring/prometheus/rules monitoring/alertmanager monitoring/grafana/provisioning
cp templates/observability/docker-compose.observability.yml.template      docker-compose.observability.yml
cp templates/observability/prometheus/prometheus.yml.template             monitoring/prometheus/prometheus.yml
cp templates/observability/prometheus/rules/app-alerts.yml.template       monitoring/prometheus/rules/app-alerts.yml
cp templates/observability/alertmanager/alertmanager.yml.template         monitoring/alertmanager/alertmanager.yml
```

## Quick start

```bash
# Network (jednorazowo):
task monitor:net

# Bring up full stack:
task monitor:up
# albo: docker compose -f docker-compose.observability.yml up -d

# Check status:
task monitor:status

# Stop:
task monitor:down
```

Następnie:

- Grafana → <http://localhost:3000> (anonymous viewer — Loki + Prometheus auto-provisioned)
- Prometheus → <http://localhost:9090>
- Alertmanager → <http://localhost:9093>
- Uptime Kuma → <http://localhost:3001>
- Healing webhook → <http://localhost:8810/health>

## Healing webhook integration

`healing-webhook` (services/healing-webhook/) odbiera alerty z
Alertmanager pod `/alertmanager` i:

1. Tworzy planfile ticket (default, no LLM call)
2. Opcjonalnie wywołuje redsl improve (dry-run, single action)
3. Opcjonalnie wywołuje rebuild restore <endpoint>

Pełny workflow: [`workflows/observability-bootstrap.md`](../../workflows/observability-bootstrap.md).

## Reference deployment (c2004)

c2004 ma prawie identyczny stack:

- 11 services (dodatkowo `testql-watchdog` → ciągłe scenariusze)
- Custom dashboards w `monitoring/grafana/dashboards/`
- `docker-compose.observability.yml` — 11 containers
- `monitoring/prometheus/rules/c2004-alerts.yml` — 20+ alert rules
