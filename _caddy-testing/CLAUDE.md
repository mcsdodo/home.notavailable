# Remote Access

**Test Hosts** (SSH passwordless with keys):
- host1: `ssh root@192.168.0.96` - Server mode (Caddy + Agent)
- host2: `ssh root@192.168.0.98` - Agent mode
- host3: `ssh root@192.168.0.99` - Agent mode

IMPORTANT: Developed on Windows, must work on Linux.

---

# Markdown file naming
When creating new files in this directory, use XX-[FILE_NAME].md format (e.g. 01-TASK.md) for easy sorting. Increment XX as needed.

# Caddy Multi-Host Agent System

> Python-based agent system for multi-host Docker reverse proxying without orchestration.

## Status: ✅ Deployed & Tested

**Last Updated**: 2025-11-16
**Deployment**: 3 hosts operational
**Docs**: [03-README-MULTIHOST.md](03-README-MULTIHOST.md) | [02-IMPLEMENTATION-PLAN.md](02-IMPLEMENTATION-PLAN.md)

## Current Deployment

| Host | IP | Role | Services |
|------|------|------|----------|
| host1 | 192.168.0.96 | Server | Caddy, Agent (server mode), test-local |
| host2 | 192.168.0.98 | Agent | Agent, test-remote |
| host3 | 192.168.0.99 | Agent | Agent, test-host3 |

**Active Routes**:
- `test-local.lan` → localhost:8081 (host1)
- `test-remote.lan` → 192.168.0.98:8080 (host2)
- `test-host3.lan` → 192.168.0.99:9000 (host3)

All accessible via host1's Caddy server (port 80/443).

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
- `AGENT_MODE`: standalone|server|agent
- `AGENT_ID`: Unique identifier (default: hostname)
- `CADDY_SERVER_URL`: Remote Caddy API URL (agent mode)
- `HOST_IP`: Host IP for routing (auto-detected)
- `DOCKER_LABEL_PREFIX`: Label prefix (default: caddy)

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
# host1 (builds from local image)
scp caddy-agent.tar.gz docker-compose-prod-server.yml Caddyfile root@192.168.0.96:/root/caddy-multihost/
ssh root@192.168.0.96 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-server.yml up -d"

# host2
scp caddy-agent.tar.gz docker-compose-prod-agent2.yml root@192.168.0.98:/root/caddy-multihost/
ssh root@192.168.0.98 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-agent2.yml up -d"

# host3
scp caddy-agent.tar.gz docker-compose-prod-agent3.yml root@192.168.0.99:/root/caddy-multihost/
ssh root@192.168.0.99 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-agent3.yml up -d"
```

## Quick Commands

**Build image**:
```bash
docker build -t caddy-agent:latest .
docker save caddy-agent:latest | gzip > caddy-agent.tar.gz
```

**Check routes**:
```bash
curl -s http://192.168.0.96:2019/config/apps/http/servers/reverse_proxy/routes
```

**Test routing**:
```bash
curl -H "Host: test-remote.lan" http://192.168.0.96
```

**View logs**:
```bash
ssh root@192.168.0.96 "docker logs caddy-agent-server --tail 20"
ssh root@192.168.0.98 "docker logs caddy-agent-remote --tail 20"
```

## Known Issues

1. **Sysctl setting required**: `sysctl -w net.ipv4.ip_unprivileged_port_start=80` on all hosts
2. **Manual config push needed**: Agent reports success but routes don't update - needs investigation
3. **Published ports required**: Agent mode containers must publish ports to host
4. **No API token enforcement**: Coded but not configured in Caddy

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
├── caddy-agent-watch.py          # Core agent
├── Dockerfile                     # Agent image
├── Caddyfile                      # Minimal Caddy config
├── docker-compose-prod-*.yml     # Production deployments
├── README-MULTIHOST.md           # User documentation
├── CLAUDE.md                      # This file (dev context)
├── IMPLEMENTATION-PLAN.md        # Task tracking
└── TESTING-RESULTS.md            # Test results
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

---

**Version**: 1.0 - Production Deployment
**Status**: ✅ Working with known issues
