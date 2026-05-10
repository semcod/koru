---
description: Bootstrap full observability + self-healing stack (Prometheus + Grafana + Loki + healing-webhook)
---

# Observability bootstrap

Bootstrap **production-grade monitoring + self-healing** w jednym repo z
templates koru. Pattern przeniesiony z c2004 production deployment.

```text
┌─────────────────────────────────────────────────────────────────────┐
│  PROMETHEUS  ←──── scrape ────  app metrics + cadvisor + node-exp   │
│      ↓                                                               │
│  ALERTS (rules) ──→ ALERTMANAGER ──→ HEALING-WEBHOOK                 │
│                                          ↓                           │
│                          alert routing → planfile ticket /           │
│                                          redsl improve /             │
│                                          rebuild restore             │
│                                                                      │
│  LOKI ←──── promtail ──── /var/lib/docker/containers logs            │
│      ↓                                                               │
│  GRAFANA ←── data source ── PROMETHEUS + LOKI                        │
│                                                                      │
│  UPTIME-KUMA — independent simple uptime UI (browser-based config)   │
└─────────────────────────────────────────────────────────────────────┘
```

## Deployment checklist

### Krok 1. Skopiuj templates

```bash
task template:install:observability
# albo ręcznie:
mkdir -p monitoring/prometheus/rules monitoring/alertmanager monitoring/grafana/provisioning
cp templates/observability/docker-compose.observability.yml.template      docker-compose.observability.yml
cp templates/observability/prometheus/prometheus.yml.template             monitoring/prometheus/prometheus.yml
cp templates/observability/prometheus/rules/app-alerts.yml.template       monitoring/prometheus/rules/app-alerts.yml
cp templates/observability/alertmanager/alertmanager.yml.template         monitoring/alertmanager/alertmanager.yml
```

### Krok 2. Substituuj placeholdery

```bash
APP_NAME=myapp
APP_PORT=8000

find docker-compose.observability.yml monitoring/ -type f | \
  xargs sed -i \
    -e "s/<APP_NAME>/${APP_NAME}/g" \
    -e "s/<APP_PORT>/${APP_PORT}/g"
```

### Krok 3. Dostosuj Prometheus scrape config

Edit `monitoring/prometheus/prometheus.yml` — dodaj swoje endpointy do
`scrape_configs:` i `blackbox-http` static_configs.

### Krok 4. Dostosuj alert rules

Edit `monitoring/prometheus/rules/app-alerts.yml`:

- Thresholds (default: 5% error rate, 90% memory, etc.)
- Healing strategies (`ticket_create` / `redsl_improve` / `annotate`)
- Custom alerts dla swojej domeny (np. `BackendDBDown`, `QueueLag`...)

### Krok 5. (Opcjonalnie) Healing webhook

Templates zakładają że masz `services/healing-webhook/` w repo. Jeśli nie
masz:

```bash
# Skopiuj baseline z koru:
cp -r /path/to/koru/services/healing-webhook services/

# Albo wyłącz w docker-compose:
sed -i '/healing-webhook:/,/networks: \[quality-net\]/d' docker-compose.observability.yml
sed -i 's|alertmanager.*healing-webhook.*|# webhook dropped|g' monitoring/alertmanager/alertmanager.yml
```

### Krok 6. Stwórz network + bring up

```bash
task monitor:net           # create c2004-quality-net
task monitor:up            # full 10-service stack
task monitor:status        # check all running
```

### Krok 7. Browser checks

| URL | Co zobaczysz |
|---|---|
| <http://localhost:9090> | Prometheus (scrape targets, alert rules) |
| <http://localhost:9093> | Alertmanager (active alerts, silences) |
| <http://localhost:3000> | Grafana (anonymous viewer, Prometheus + Loki sources) |
| <http://localhost:3001> | Uptime Kuma (browser config first time) |
| <http://localhost:8810/health> | Healing webhook health |

### Krok 8. Test alert flow

```bash
# Manualnie wywołaj alert:
curl -X POST http://localhost:9093/api/v2/alerts -d '[{
  "labels": {
    "alertname": "TestEndpointDown",
    "severity": "critical",
    "component": "endpoint",
    "healing_strategy": "ticket_create",
    "instance": "test"
  },
  "annotations": {"summary": "Manual test alert"}
}]'

# Po ~30s sprawdź czy ticket powstał:
task tickets:list           # powinien być TestEndpointDown
```

### Krok 9. Weryfikacja end-to-end

```bash
docker ps --filter "name=<APP_NAME>-" --format "table {{.Names}}\t{{.Status}}"
# Oczekiwane: 10 running containers

curl -fsS http://localhost:9090/-/healthy && echo "OK: Prometheus"
curl -fsS http://localhost:9093/-/healthy && echo "OK: Alertmanager"
curl -fsS http://localhost:3000/api/health && echo "OK: Grafana"
curl -fsS http://localhost:3100/ready && echo "OK: Loki"
curl -fsS http://localhost:8810/health && echo "OK: Healing webhook"
```

## Alert healing strategies

`healing-webhook` rozpoznaje labele alertów i decyduje action:

| `healing_strategy` label | Akcja |
|---|---|
| `annotate` | POST Grafana annotation, no code change |
| `ticket_create` | Open planfile ticket (default for product alerts) |
| `redsl_gate` | Run `redsl gate check`, log output |
| `redsl_improve` | Run `redsl improve --max-actions 1` (dry-run) |
| `rebuild_restore` | `rebuild restore <endpoint>` from last green walk |
| `redup_check` | `task quality:redup:check` + ticket if budget breached |

## Customization

### Dodatkowe scrape targets

```yaml
# monitoring/prometheus/prometheus.yml
- job_name: my-custom-service
  static_configs:
    - targets: ['host.docker.internal:9999']
      labels:
        component: custom
```

### Dodatkowe Grafana dashboards

```bash
mkdir -p monitoring/grafana/dashboards
# Skopiuj swoje JSON dashboards lub provision via:
cat > monitoring/grafana/provisioning/dashboards.yml <<EOF
apiVersion: 1
providers:
  - name: 'My App'
    folder: '<APP_NAME>'
    type: file
    options:
      path: /var/lib/grafana/dashboards
EOF
```

### Custom alert rules

Dodaj plik do `monitoring/prometheus/rules/`:

```yaml
# monitoring/prometheus/rules/my-domain.yml
groups:
  - name: <APP_NAME>-domain
    rules:
      - alert: MyCustomCondition
        expr: my_metric > 100
        for: 5m
        labels:
          severity: warning
          healing_strategy: ticket_create
```

Reload Prometheus bez restartu:

```bash
curl -X POST http://localhost:9090/-/reload
```

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `Cannot connect to host.docker.internal` | Add `extra_hosts: ["host.docker.internal:host-gateway"]` do swojej service |
| Grafana nie widzi Prometheus | Sprawdź czy oba są w `<APP_NAME>-quality-net` (`docker network inspect`) |
| Alerts firing ale brak ticketów | `docker logs <APP_NAME>-healing-webhook` — sprawdź czy URL Alertmanager-a poprawny |
| Loki out of disk | Lower retention: `command: -table-manager.retention-period=24h` |
| Promtail nie szyfruje logów | Check that mountpoints `/var/log` i `/var/lib/docker/containers` istnieją + dostępne |

## Odroll / disable

```bash
task monitor:down           # stop all
docker network rm <APP_NAME>-quality-net
rm -rf docker-compose.observability.yml monitoring/
```

## Reference

c2004 stack:

- 11 services (dodatkowo `testql-watchdog` dla ciągłych scenariuszy)
- 20+ alert rules w `monitoring/prometheus/rules/c2004-alerts.yml`
- Healing webhook z 5 strategiami (`heal_redup_check`, `heal_redsl_gate`, ...)
- Custom Grafana dashboards w `monitoring/grafana/dashboards/`
- Loki retention: 14 dni
- Prometheus retention: 14 dni
