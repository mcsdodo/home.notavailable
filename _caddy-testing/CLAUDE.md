# Remote Access

**Test Hosts** (SSH passwordless with keys):
- host1: `ssh root@192.168.0.96` - Server mode (Caddy + Agent)
- host2: `ssh root@192.168.0.98` - Agent mode
- host3: `ssh root@192.168.0.99` - Agent mode

**Production Hosts** (SSH passwordless with keys):
- prod-host1: `ssh root@192.168.0.112` - Server mode (Caddy + Agent)
- prod-host2: `ssh root@192.168.0.235` - Agent mode
- prod-host3: `ssh root@192.168.0.212` - Agent mode

IMPORTANT: Developed on Windows, must work on Linux.

---

# **IMPORTANT**  Markdown file naming
When creating new files in this directory, use XX-[FILE_NAME].md format (e.g. 01-TASK.md) for easy sorting. Increment XX as needed.

# Caddy Multi-Host Agent System

> Python-based agent system for multi-host Docker reverse proxying without orchestration.

## Architecture

```
host1 (.96) - SERVER
├─ Caddy (80/443/2019)
├─ Agent (server mode)
└─ Containers
        ▲
        │ HTTP POST :2019/load
    ┌───┴───┐
host2 (.98) host3 (.99)
Agent       Agent
Containers  Containers
```

**Key Concept**: Agents watch Docker, POST routes to main Caddy via Admin API.

## Core Components

**[caddy-agent-watch.py](caddy-agent-watch.py)** - Agent with 3 modes:
- `standalone` - Local Docker → Local Caddy
- `server` - Local Docker → Local Caddy (accepts remote updates)
- `agent` - Local Docker → Remote Caddy

**Environment Variables**:
- `CADDY_URL`: Caddy Admin API endpoint (default: http://localhost:2019)
- `HOST_IP`: IP for upstreams; enables remote mode. Auto-detects with network_mode: host
- `AGENT_ID`: Unique identifier (default: hostname)
- `DOCKER_LABEL_PREFIX`: Label prefix (default: caddy)
- `CADDY_API_TOKEN`: Bearer token for authentication (optional)
- `AGENT_FILTER_LABEL`: Filter containers by label (optional)

**Docker Compose Files**:
- `docker-compose-prod-server.yml` - Server deployment
- `docker-compose-prod-agent2.yml` - Agent deployment (host2)
- `docker-compose-prod-agent3.yml` - Agent deployment (host3)

## How It Works

1. Agent watches Docker events
2. Reads `caddy` labels from containers
3. Maps container ports to host published ports (agent mode)
4. Tags routes with `@id: {AGENT_ID}_{container_name}`
5. POSTs config to Caddy Admin API
6. Caddy merges routes (keeps other agents, updates own)

**Route Merging**: Agent ID prefixing prevents conflicts between agents.

## Production Files

All compose files use `network_mode: host` to avoid Docker port binding issues.

**Deploy**:
```bash
# Build image first
docker build -t caddy-agent:latest .
docker save caddy-agent:latest | gzip > caddy-agent.tar.gz

# host1 - Server (Caddy + Agent + test services)
scp caddy-agent.tar.gz caddy-config.json docker-compose-prod-server.yml root@192.168.0.96:/root/caddy-multihost/
ssh root@192.168.0.96 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-server.yml up -d"

# host2 - Agent (remote agent + test services)
scp caddy-agent.tar.gz docker-compose-prod-agent2.yml root@192.168.0.98:/root/caddy-multihost/
ssh root@192.168.0.98 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-agent2.yml up -d"

# host3 - Agent (bridge mode + test services)
scp caddy-agent.tar.gz docker-compose-prod-agent3.yml root@192.168.0.99:/root/caddy-multihost/
ssh root@192.168.0.99 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-agent3.yml up -d"
```

## Comprehensive Testing Guide

### Test Servers

- **srv0** (:2020) - Admin API proxy
- **srv1** (:443, :8080) - Main HTTPS server (uses internal CA for .lan domains)
- **srv2** (:80) - HTTP-only server

### Test Execution

Run tests from a Linux host (Windows curl has SNI issues with IP addresses):
```bash
# SSH to host2 for testing
ssh root@192.168.0.98
```

### Phase 1: Basic Label Tests

```bash
# Simple labels (caddy: domain.lan)
curl -sk --resolve test-local.lan:443:192.168.0.96 https://test-local.lan      # host1
curl -sk --resolve test-remote.lan:443:192.168.0.96 https://test-remote.lan    # host2
curl -sk --resolve test-host3.lan:443:192.168.0.96 https://test-host3.lan      # host3

# Numbered labels (caddy_0, caddy_1, etc.)
curl -sk --resolve test-numbered-0.lan:443:192.168.0.96 https://test-numbered-0.lan
curl -sk --resolve host2-route10.lan:443:192.168.0.96 https://host2-route10.lan
curl -sk --resolve host2-route111.lan:443:192.168.0.96 https://host2-route111.lan

# Multi-domain labels (caddy: domain1.lan, domain2.lan)
curl -sk --resolve test-multi-a.lan:443:192.168.0.96 https://test-multi-a.lan
curl -sk --resolve host2-app1.lan:443:192.168.0.96 https://host2-app1.lan

# Mixed simple + numbered
curl -sk --resolve host3-simple.lan:443:192.168.0.96 https://host3-simple.lan
curl -sk --resolve host3-numbered5.lan:443:192.168.0.96 https://host3-numbered5.lan
```

### Phase 2: Route Ordering Tests

Specific routes should match before wildcard `*.test.lan`:
```bash
# Should return "SUCCESS - Specific route matched"
curl -sk --resolve app.test.lan:443:192.168.0.96 https://app.test.lan
curl -sk --resolve api.test.lan:443:192.168.0.96 https://api.test.lan

# Should return "Wildcard catch-all for *.test.lan"
curl -sk --resolve random.test.lan:443:192.168.0.96 https://random.test.lan
```

### Phase 3: HTTP-only Routes

Routes with `http://` prefix go to srv2 (port 80):
```bash
# HTTP-only route (srv2 on :80)
curl -s --resolve httponly.test.lan:80:192.168.0.96 http://httponly.test.lan

# Regular HTTPS route (srv1 on :443)
curl -sk --resolve https.test.lan:443:192.168.0.96 https://https.test.lan
```

### Phase 4: Advanced Features

```bash
# Header manipulation
curl -sk --resolve phase3-headers.lan:443:192.168.0.96 https://phase3-headers.lan

# Transport TLS config (requires TLS-enabled backend - empty response expected for http-echo)
curl -sk --resolve phase2-transport.lan:443:192.168.0.96 https://phase2-transport.lan
```

### Verify Routes Registered

```bash
# Check srv1 (HTTPS) routes
curl -s http://192.168.0.96:2019/config/apps/http/servers/srv1/routes | python -m json.tool

# Check srv2 (HTTP-only) routes
curl -s http://192.168.0.96:2019/config/apps/http/servers/srv2/routes | python -m json.tool

# Check agent logs
ssh root@192.168.0.96 "docker logs caddy-agent-server --tail 10"
ssh root@192.168.0.98 "docker logs caddy-agent-remote --tail 10"
ssh root@192.168.0.99 "docker logs caddy-agent-remote3 --tail 10"
```

### Restart After Config Changes

```bash
# After updating caddy-config.json, restart Caddy then agents
ssh root@192.168.0.96 "cd /root/caddy-multihost && docker compose -f docker-compose-prod-server.yml restart caddy"
ssh root@192.168.0.96 "docker restart caddy-agent-server"
ssh root@192.168.0.98 "docker restart caddy-agent-remote"
ssh root@192.168.0.99 "docker restart caddy-agent-remote3"
```

## Quick Commands

**Check routes**:
```bash
curl -s http://192.168.0.96:2019/config/apps/http/servers/srv1/routes | python -m json.tool
```

**View logs**:
```bash
ssh root@192.168.0.96 "docker logs caddy-agent-server --tail 20"
ssh root@192.168.0.98 "docker logs caddy-agent-remote --tail 20"
ssh root@192.168.0.99 "docker logs caddy-agent-remote3 --tail 20"
```

## Known Issues

1. **Manual config push needed**: Agent reports success but routes don't update - needs investigation
2. **Published ports required**: Agent mode containers must publish ports to host
3. **No API token enforcement**: Coded but not configured in Caddy

## Next Steps (Priority 1)

See [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) for details.

- [ ] Fix automatic route updates (currently requires manual push)
- [ ] Add retry logic for failed updates
- [ ] Implement API token authentication
- [ ] Add stale route cleanup (heartbeat)
- [ ] Real-world multi-host testing with VPN

## File Structure

```
_caddy-testing/
├── caddy-agent-watch.py          # Core agent script
├── Dockerfile                     # Agent image build
├── caddy-config.json             # Caddy JSON config (srv0/srv1/srv2)
├── docker-compose-prod-server.yml # host1: Caddy + Agent + tests
├── docker-compose-prod-agent2.yml # host2: Agent + tests (network_mode: host)
├── docker-compose-prod-agent3.yml # host3: Agent + tests (bridge mode)
└── CLAUDE.md                      # This file
```

## Debugging

**Agent can't connect**:
```bash
curl http://192.168.0.96:2019/config/
```

**Check container labels**:
```bash
docker inspect <container> | jq '.Config.Labels'
```

**Manual config push** (workaround for update issue):
```bash
docker exec caddy-agent-server curl -X POST -H 'Content-Type: application/json' -d @/app/caddy-output.json http://localhost:2019/load
```