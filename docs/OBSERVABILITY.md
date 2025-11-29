# Observability with LGTM Stack

**Status**: Ready to Deploy
**Last Updated**: 2025-11-24

---

## Overview

The Agent-Spike platform uses the **LGTM stack** (Loki, Grafana, Tempo, Prometheus) for unified observability. This provides:

1. **Debugging**: Structured logs with correlation IDs via Loki
2. **Performance Monitoring**: Metrics and dashboards via Prometheus + Grafana
3. **Distributed Tracing**: Request flows via Tempo
4. **AI Agent Analysis**: Programmatic queries (LogQL/PromQL) for outcome tracking and calibration

---

## Architecture

```
┌─────────────────┐
│   Frontend      │  (Browser tracing via OpenTelemetry)
│   (Svelte)      │  - Auto-instrument fetch() calls
└────────┬────────┘  - Structured console logging
         │           - Send critical errors to backend
         ▼
┌─────────────────┐
│   API Service   │  (FastAPI with OpenTelemetry)
│   (Python)      │  - Structured JSON logging
└────────┬────────┘  - Distributed tracing
         │           - Correlation ID middleware
         │           - Prometheus metrics
         ▼
┌─────────────────┐
│ OTLP Collector  │  (OpenTelemetry Collector)
│ (OTel)          │  Ports: 4317 (gRPC), 4318 (HTTP)
└─────┬───┬───┬───┘  Forwards to:
      │   │   │
      │   │   └──────► Tempo (traces)
      │   └──────────► Prometheus (metrics)
      └──────────────► Loki (logs)
                       │
         ┌─────────────┴────────────┐
         ▼                          ▼
┌─────────────────┐        ┌─────────────────┐
│   Loki          │        │  Prometheus     │
│   (Logs)        │        │  (Metrics)      │
│   Port: 3100    │        │  Port: 9090     │
└────────┬────────┘        └────────┬────────┘
         │                          │
         │        ┌─────────────────┤
         │        │                 │
         ▼        ▼                 ▼
┌─────────────────────────────────────┐
│           Grafana UI                │
│   http://192.168.16.241:3000       │
│   - Logs (Loki datasource)          │
│   - Metrics (Prometheus datasource) │
│   - Traces (Tempo datasource)       │
└─────────────────────────────────────┘
```

---

## Deployment

### Prerequisites

- Ansible installed on local machine
- SSH access to GPU server (192.168.16.241)
- Docker and Docker Compose on GPU server

### Deploy LGTM Stack

```bash
# Deploy observability stack to GPU server
make gpu-deploy-observability

# Verify services are running
ssh user@192.168.16.241 'docker ps | grep -E "loki|prometheus|tempo|grafana|otel"'
```

### Access Services

- **Grafana UI**: http://192.168.16.241:3000 (admin/admin)
- **Prometheus**: http://192.168.16.241:9090
- **Loki**: http://192.168.16.241:3100
- **Tempo**: http://192.168.16.241:3200
- **OTLP Collector**: 192.168.16.241:4317 (gRPC), 192.168.16.241:4318 (HTTP)

### Verify Deployment

```bash
# Check Grafana
curl http://192.168.16.241:3000/api/health

# Check Loki
curl http://192.168.16.241:3100/ready

# Check Prometheus
curl http://192.168.16.241:9090/-/healthy

# Check Tempo
curl http://192.168.16.241:3200/ready
```

---

## Python Backend Instrumentation

### Setup (Already Configured)

The API service is already configured with:
- **Structured JSON logging** (`compose/lib/logging_config.py`)
- **OpenTelemetry tracing** (`compose/lib/telemetry.py`)
- **Correlation ID middleware** (`compose/api/middleware/correlation.py`)

### Environment Variables

Update `.env` (root, git-crypt encrypted):

```bash
# OTLP Collector endpoint
OTLP_ENDPOINT=http://192.168.16.241:4317

# Observability UI URLs
GRAFANA_URL=http://192.168.16.241:3000
PROMETHEUS_URL=http://192.168.16.241:9090
LOKI_URL=http://192.168.16.241:3100

# Grafana admin password (optional, defaults to "admin")
GRAFANA_ADMIN_PASSWORD=<secure-password>
```

### Restart API

After updating `.env`:

```bash
make rebuild-api
```

---

## Frontend Instrumentation

### Current Status

- ✅ Structured logger implemented (`compose/frontend/src/lib/logger.ts`)
- ✅ OpenTelemetry setup implemented (`compose/frontend/src/lib/telemetry.ts`)
- ❌ **Not yet initialized** in main app

### Enable Frontend Observability

Add to `compose/frontend/src/routes/+layout.svelte`:

```svelte
<script>
  import { onMount } from 'svelte';
  import { setupTelemetry } from '$lib/telemetry';

  onMount(() => {
    setupTelemetry();
  });
</script>
```

---

## Agent Analysis with LGTMClient

### Query Observability Data

The `LGTMClient` provides programmatic access to observability data for AI agents:

```python
from compose.services.observability import LGTMClient

async with LGTMClient() as lgtm:
    # Query error patterns (outcome tracking)
    errors = await lgtm.query_error_patterns(
        service_name="agent-spike-api",
        lookback_hours=24,
        min_count=5
    )

    # Query performance bottlenecks (calibration)
    bottlenecks = await lgtm.query_performance_bottlenecks(
        service_name="agent-spike-api",
        p95_threshold_ms=1000
    )

    # Query service health
    health = await lgtm.query_service_health("agent-spike-api")

    # Query usage patterns
    usage = await lgtm.query_usage_patterns(
        service_name="agent-spike-api",
        top_n=10
    )
```

### API Endpoint

The `/stats` endpoint provides observability metrics:

```bash
curl http://localhost:8000/stats
```

Response:
```json
{
  "status": "healthy",
  "service_name": "agent-spike-api",
  "error_rate": 0.5,
  "avg_response_time_ms": 125.3,
  "requests_per_minute": 45.2,
  "issues": [],
  "top_errors": [...],
  "slowest_endpoints": [...]
}
```

---

## Grafana Dashboards

### Pre-configured Datasources

The deployment automatically configures:
- **Loki** - Logs datasource
- **Prometheus** - Metrics datasource
- **Tempo** - Traces datasource

All datasources are linked:
- Click a log → See related traces
- Click a trace → See related logs
- Service map powered by Prometheus metrics

### Creating Dashboards

1. Access Grafana: http://192.168.16.241:3000
2. Navigate to Dashboards → New Dashboard
3. Add panels using:
   - **Loki** for log queries (LogQL)
   - **Prometheus** for metrics (PromQL)
   - **Tempo** for traces

### Example Queries

**LogQL** (Loki - find errors):
```logql
{service_name="agent-spike-api", level="error"} | json
```

**PromQL** (Prometheus - request rate):
```promql
rate(http_requests_total{service_name="agent-spike-api"}[5m])
```

---

## Troubleshooting

### No Data Appearing in Grafana

1. **Check OTLP Collector**:
   ```bash
   ssh user@192.168.16.241 'docker logs otel-collector'
   ```

2. **Check OTLP_ENDPOINT**:
   ```bash
   # Should point to GPU server
   grep OTLP_ENDPOINT .env
   ```

3. **Verify API is sending telemetry**:
   ```bash
   make logs-api | grep -i "otel\|telemetry"
   ```

### Services Not Starting

```bash
# Check logs for each service
ssh user@192.168.16.241 'cd /apps/observability && docker compose logs'
```

### High Memory Usage

- **Loki**: Reduce retention in `tempo.yaml` (default: 7 days)
- **Prometheus**: Reduce scrape interval in `prometheus.yml`
- **Tempo**: Reduce block retention in `tempo.yaml`

---

## Next Steps

- [x] Deploy LGTM stack to GPU server
- [ ] Restart API with updated `.env`
- [ ] Initialize frontend telemetry
- [ ] Create Grafana dashboards
- [ ] Configure alerts (Prometheus Alertmanager)
- [ ] Test agent analysis queries
- [ ] Replace remaining `print()` statements with structured logging

---

## Migration Notes

### From SigNoz

This project previously used SigNoz but migrated to LGTM stack due to deployment complexity. Key differences:

- **SigNoz**: Unified platform (ClickHouse backend)
- **LGTM**: 4 separate services (simpler, more flexible)
- **API compatibility**: Both use OpenTelemetry (no instrumentation changes needed)
- **Agent queries**: `SigNozClient` → `LGTMClient` (LogQL/PromQL instead of SQL)
