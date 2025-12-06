# Centralized Observability Setup

Collects logs and metrics from all Docker containers across multiple hosts using Grafana Alloy, Loki, and Prometheus.

## Architecture

- **Central Stack** (one host): Loki (logs), Prometheus (metrics), Grafana (UI)
- **Alloy Agent** (each host): Collects container logs and metrics, sends to central stack
- **Auto-discovery**: Monitors all containers via Docker socket, zero per-service config
- **Retention**: 30 days for logs and metrics

## Deployment

### 1. Central Stack

Deploy `portainer.stacks/observability` stack in Portainer on your main host.

Creates:
- Loki: https://loki.lacny.me (port 3100)
- Prometheus: https://prometheus.lacny.me (port 9090)
- Grafana: https://grafana.lacny.me (port 3000)

### 2. Alloy Agent (Each Host)

Deploy `portainer.stacks/docker-host-infra` stack on every Docker host with these environment variables:

**Local (same host as central stack):**
```env
LOKI_URL=http://loki:3100
PROMETHEUS_URL=http://prometheus:9090
ALLOY_HOSTNAME=docker-host-1
```

**Remote hosts:**
```env
LOKI_URL=https://loki.lacny.me
PROMETHEUS_URL=https://prometheus.lacny.me
ALLOY_HOSTNAME=media-server
```

Set `ALLOY_HOSTNAME` to a unique identifier for each host.

### 3. Verify

Open Grafana → Explore → Loki → Query: `{hostname="docker-host-1"}`

## Configuration Files

### Central Stack (`portainer.stacks/observability/`)
- `docker-compose.yml` - Loki, Prometheus, Grafana services
- `loki-config.yml` - Loki config (deployed to `/mnt/shared_configs/grafana/`)
- `prometheus-config.yml` - Prometheus config (deployed to `/mnt/shared_configs/grafana/`)

### Alloy Agent (`portainer.stacks/docker-host-infra/`)
- `docker-compose.yml` - Alloy service with environment variables
- `alloy/config.alloy` - Alloy configuration (deployed to `/mnt/shared_configs/grafana/config.alloy`)
- `alloy/.env.example` - Environment variable template

## Labels

Alloy automatically extracts these labels from Docker containers:

- `hostname` - From `ALLOY_HOSTNAME` env var
- `service_name` - From Docker Compose service name (`com.docker.compose.service`)
- `compose_project` - From Docker Compose project name (`com.docker.compose.project`)
- `container_name` - Container name

## Query Examples

### Logs (Loki)

```logql
# All logs from specific host
{hostname="media-server"}

# Logs from specific service
{service_name="radarr"}

# Logs from compose stack
{compose_project="arr"}

# Search for errors
{hostname="surveillance"} |= "error"

# Multiple filters
{hostname="arr-stack", service_name="radarr"} |= "download"
```

### Metrics (Prometheus)

```promql
# CPU usage per container
rate(container_cpu_usage_seconds_total{hostname="media-server"}[5m])

# Memory usage
container_memory_usage_bytes{hostname="media-server"}

# Network traffic
rate(container_network_receive_bytes_total{hostname="surveillance"}[5m])

# Top 5 CPU consumers
topk(5, rate(container_cpu_usage_seconds_total[5m]))
```

## Retention

Change retention in `portainer.stacks/observability/`:

**Logs** (`loki-config.yml`):
```yaml
limits_config:
  retention_period: 720h  # 30 days (in hours)
```

**Metrics** (`docker-compose.yml` prometheus service):
```yaml
command:
  - '--storage.tsdb.retention.time=30d'
```

## Troubleshooting

### No logs appearing

```bash
# Check Alloy logs
docker logs alloy

# Verify Alloy can reach Loki
docker exec alloy wget -O- $LOKI_URL/ready

# Check discovered containers
curl https://alloy.lacny.me/api/v0/web/components

# Check labels in Loki
curl https://loki.lacny.me/loki/api/v1/labels
curl https://loki.lacny.me/loki/api/v1/label/service_name/values
```

### No metrics appearing

```bash
# Check Prometheus health
curl https://prometheus.lacny.me/-/healthy

# Check Alloy metrics pipeline
docker logs alloy | grep prometheus
```

## Resource Usage

**Per host:**
- Alloy: ~150MB RAM, ~1-2% CPU

**Central stack:**
- Loki: ~300MB RAM
- Prometheus: ~500MB RAM
- Grafana: ~150MB RAM
