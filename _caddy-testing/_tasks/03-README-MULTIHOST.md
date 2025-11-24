# Multi-Host Caddy Docker Proxy

A solution for automatic reverse proxying of Docker containers across multiple hosts using Caddy and a Python-based agent system.

## Overview

This project extends Caddy's reverse proxy capabilities to work across multiple Docker hosts without requiring Docker Swarm or Kubernetes. It uses an agent-based architecture where:

- **Main Server**: Runs Caddy with Admin API enabled, handles all proxying
- **Remote Agents**: Watch Docker containers on remote hosts and report to the main server

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Docker Host 1 (Main Server)                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Caddy Server                                         │  │
│  │  - Admin API (:2019)                                 │  │
│  │  - Handles all HTTP/HTTPS traffic                    │  │
│  │  - Receives route updates from agents                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Caddy Agent (Standalone Mode)                        │  │
│  │  - Watches local Docker containers                   │  │
│  │  - Updates local Caddy config                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ HTTP API
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────┼────────────┐              ┌──────────┼────────┐
│ Host 2│            │              │ Host 3   │        │
│  ┌────┴─────────┐  │              │  ┌───────┴─────┐  │
│  │ Agent        │  │              │  │ Agent       │  │
│  │ (Agent Mode) │  │              │  │ (Agent Mode)│  │
│  │              │  │              │  │             │  │
│  │ - Watch      │  │              │  │ - Watch     │  │
│  │   Docker     │  │              │  │   Docker    │  │
│  │ - POST to    │  │              │  │ - POST to   │  │
│  │   main server│  │              │  │   server    │  │
│  └──────────────┘  │              │  └─────────────┘  │
└────────────────────┘              └────────────────────┘
```

## Features

- ✅ **Label-based configuration** - Use Docker labels like current caddy-docker-proxy
- ✅ **Multi-host support** - Proxy containers across multiple Docker hosts
- ✅ **No orchestrator required** - Works without Swarm or Kubernetes
- ✅ **Automatic discovery** - Watches Docker events for container changes
- ✅ **Zero downtime updates** - Routes update dynamically via Caddy Admin API
- ✅ **Agent identification** - Tracks which agent manages which routes
- ✅ **Flexible networking** - Works over Tailscale, VPN, or direct connections

## Agent Modes

### Standalone Mode (Default)
- Watches local Docker socket
- Updates local Caddy instance
- Current behavior, backward compatible

### Server Mode
- Same as standalone but designed to receive updates from remote agents
- Runs Caddy with Admin API exposed

### Agent Mode
- Watches local Docker socket on remote host
- Reports container info to remote Caddy server
- Uses published ports for routing

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_MODE` | `standalone` | Mode: `standalone`, `server`, or `agent` |
| `AGENT_ID` | hostname | Unique identifier for this agent |
| `CADDY_API_URL` | `http://caddy:2019` | Local Caddy API URL (standalone/server mode) |
| `CADDY_SERVER_URL` | `http://localhost:2019` | Remote Caddy API URL (agent mode) |
| `CADDY_API_TOKEN` | _(empty)_ | Bearer token for API authentication |
| `HOST_IP` | _(auto-detect)_ | Host IP address for routing (agent mode) |
| `DOCKER_LABEL_PREFIX` | `caddy` | Docker label prefix to watch |
| `AGENT_FILTER_LABEL` | _(empty)_ | Optional: filter containers by label (e.g., `agent=remote1`) |

## Quick Start

### Testing Locally (Simulating Multiple Hosts)

Build the agent image first:
```bash
docker build -t caddy-agent .
```

#### 1. Start the Main Server
```bash
docker-compose -f docker-compose-server.yml up -d
```

This starts:
- Caddy server on ports 80, 443, 2019
- Agent in standalone mode watching local containers
- Test container: `whoami-server.localhost`

#### 2. Start Remote Agent 1
```bash
docker-compose -f docker-compose-agent1.yml up -d
```

This starts:
- Agent in agent mode reporting to main server
- Test containers publishing ports 8081, 8082

#### 3. Start Remote Agent 2 (Optional)
```bash
docker-compose -f docker-compose-agent2.yml up -d
```

This starts:
- Second agent reporting to main server
- Test containers on ports 8091, 6380

### Testing the Setup

```bash
# Test local server container
curl -H "Host: whoami-server.localhost" http://localhost

# Test remote agent 1 container
curl -H "Host: whoami-remote1.localhost" http://localhost

# Test remote agent 1 alternate container
curl -H "Host: alt-remote1.localhost" http://localhost

# Test remote agent 2 container
curl -H "Host: whoami-remote2.localhost" http://localhost
```

### View Logs

```bash
# Server logs
docker-compose -f docker-compose-server.yml logs -f caddy-agent

# Agent 1 logs
docker-compose -f docker-compose-agent1.yml logs -f caddy-agent-remote1

# Agent 2 logs
docker-compose -f docker-compose-agent2.yml logs -f caddy-agent-remote2
```

## Production Deployment

### Main Server Setup

**docker-compose.yml** on main host:
```yaml
services:
  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
      - "2019:2019"  # Secure this! Use firewall or VPN
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config

  caddy-agent:
    image: your-registry/caddy-agent:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - AGENT_MODE=server
      - AGENT_ID=main-server
      - CADDY_API_URL=http://caddy:2019
```

### Remote Host Setup

**docker-compose.yml** on remote hosts:
```yaml
services:
  caddy-agent:
    image: your-registry/caddy-agent:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - AGENT_MODE=agent
      - AGENT_ID=remote-host-1
      - CADDY_SERVER_URL=https://main-server.example.com:2019
      - CADDY_API_TOKEN=your-secure-token-here
      - HOST_IP=remote-host-1.example.com
    restart: unless-stopped
```

### Security Considerations

⚠️ **Important**: The Caddy Admin API (port 2019) should NOT be exposed to the internet!

**Recommended security measures:**

1. **Use Tailscale or VPN**: Connect all hosts via private network
   ```bash
   # Example with Tailscale
   CADDY_SERVER_URL=http://main-server.tailscale-ip:2019
   ```

2. **Firewall Rules**: Only allow port 2019 from known agent IPs
   ```bash
   ufw allow from 10.0.0.0/24 to any port 2019
   ```

3. **API Token Authentication**: Set `CADDY_API_TOKEN` on all agents
   ```yaml
   environment:
     - CADDY_API_TOKEN=use-a-strong-random-token-here
   ```

4. **TLS for Admin API**: Configure Caddy Admin API with TLS
   ```caddyfile
   {
     admin https://localhost:2019 {
       cert /path/to/cert.pem
       key /path/to/key.pem
     }
   }
   ```

## Docker Label Usage

Containers must have ports **published** (exposed to host) for agent mode to work:

```yaml
services:
  my-app:
    image: my-app:latest
    ports:
      - "8080:80"  # Required for agent mode
    labels:
      - caddy=myapp.example.com
      - caddy.reverse_proxy={{upstreams 80}}
```

The agent will:
1. Read the `{{upstreams 80}}` label
2. Find published port 8080 for internal port 80
3. Create route: `myapp.example.com` → `agent-host-ip:8080`

### Supported Label Syntax

```yaml
labels:
  # Basic hostname + auto-upstream resolution
  - caddy=app.example.com
  - caddy.reverse_proxy={{upstreams 80}}

  # Multiple domains
  - caddy=app.example.com,www.app.example.com
  - caddy.reverse_proxy={{upstreams 8080}}

  # Direct upstream (not recommended for agent mode)
  - caddy=api.example.com
  - caddy.reverse_proxy=backend:3000

  # Optional: agent filter (for local development with multiple agents)
  - agent=remote1  # Only discovered by agent with AGENT_FILTER_LABEL=agent=remote1
```

### Agent Filter Label (Local Development)

When running multiple agents on the same Docker host (e.g., for testing), use `AGENT_FILTER_LABEL` to prevent agents from discovering each other's containers:

```yaml
# Agent 1
environment:
  - AGENT_MODE=agent
  - AGENT_ID=remote1
  - AGENT_FILTER_LABEL=agent=remote1

# Agent 2
environment:
  - AGENT_MODE=agent
  - AGENT_ID=remote2
  - AGENT_FILTER_LABEL=agent=remote2

# Containers for Agent 1
labels:
  - agent=remote1
  - caddy=app1.localhost
  - caddy.reverse_proxy={{upstreams 80}}

# Containers for Agent 2
labels:
  - agent=remote2
  - caddy=app2.localhost
  - caddy.reverse_proxy={{upstreams 80}}
```

**Note**: In production with separate hosts, this filter is not needed since each agent naturally only sees its own host's containers.

## Troubleshooting

### Agent can't connect to server

**Error**: `Error pushing to Caddy: ConnectionError`

**Solution**: Check network connectivity and firewall rules
```bash
# From agent host, test connection
curl http://main-server:2019/config/

# Check if using correct URL
echo $CADDY_SERVER_URL
```

### Routes not updating

**Check agent logs**:
```bash
docker logs caddy-agent-remote1 -f
```

Look for:
- `✅ Caddy config updated successfully`
- `Routes added: [...]`

**Check Caddy config**:
```bash
curl http://localhost:2019/config/ | jq .
```

### Container not found / No published port

**Error**: `No published port found for container`

**Solution**: Ensure container has published ports
```yaml
services:
  my-service:
    ports:
      - "8080:80"  # Add this!
```

### Authentication failures

**Error**: `401 Unauthorized`

**Solution**: Verify API token matches on agent and server
```bash
# Check token is set
docker exec caddy-agent-remote1 env | grep CADDY_API_TOKEN
```

## How It Works

1. **Agent watches Docker events** on local socket
2. **When containers start/stop** with Caddy labels:
   - Agent extracts domain and upstream info
   - For agent mode: maps container port to published host port
   - Creates route with agent ID in metadata
3. **Agent POSTs config** to Caddy Admin API
4. **Caddy merges routes**:
   - Keeps routes from other agents
   - Updates routes from this agent
   - Removes stopped containers
5. **Caddy applies config** with zero downtime

## Comparison with Alternatives

| Solution | Multi-Host | No Orchestrator | Label-Based | Complexity |
|----------|-----------|----------------|-------------|------------|
| **This Project** | ✅ | ✅ | ✅ | Low |
| caddy-docker-proxy controller | ✅ | ❌ (needs Swarm) | ✅ | Medium |
| Traefik + traefik-kop + Redis | ✅ | ✅ | ✅ | High |
| Consul + Service Discovery | ✅ | ✅ | ❌ | High |
| Docker Swarm | ✅ | ❌ | ✅ | Medium |
| Kubernetes | ✅ | ❌ | ✅ | Very High |

## Extending

### Adding Custom Extensions to Caddy

Build custom Caddy with extensions:

**Dockerfile.caddy**:
```dockerfile
FROM caddy:2-builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/cloudflare \
    --with github.com/mholt/caddy-l4

FROM caddy:2
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

Update docker-compose-server.yml:
```yaml
services:
  caddy:
    build:
      context: .
      dockerfile: Dockerfile.caddy
```

## Development

### Running Tests
```bash
# Start all stacks
docker-compose -f docker-compose-server.yml up -d
docker-compose -f docker-compose-agent1.yml up -d
docker-compose -f docker-compose-agent2.yml up -d

# Test all endpoints
curl -H "Host: whoami-server.localhost" http://localhost
curl -H "Host: whoami-remote1.localhost" http://localhost
curl -H "Host: whoami-remote2.localhost" http://localhost
```

### Code Structure

```
caddy-agent-watch.py
├── Configuration (lines 13-22)
├── Helper Functions
│   ├── detect_host_ip()      - Auto-detect host IP
│   ├── get_published_port()  - Map container to host port
│   └── get_target_caddy_url()- Get API URL by mode
├── Route Management
│   ├── get_caddy_routes()    - Discover containers
│   ├── push_to_caddy()       - Update Caddy config
│   └── merge_routes()        - Merge agent routes
└── Event Loop
    └── watch_docker_events() - Watch Docker events
```

## References

- [Caddy Admin API Documentation](https://caddyserver.com/docs/api)
- [caddy-docker-proxy](https://github.com/lucaslorentz/caddy-docker-proxy)
- [traefik-kop](https://github.com/jittering/traefik-kop) (inspiration)
- [Docker SDK for Python](https://docker-py.readthedocs.io/)

## License

MIT License - See TASK.md for project background and requirements.

## Contributing

Issues and pull requests welcome! This is an active development project.

---

**Status**: Working solution, tested with multiple agents. Ready for production with proper security measures.
