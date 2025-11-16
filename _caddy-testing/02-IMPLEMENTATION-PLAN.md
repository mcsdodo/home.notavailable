# Multi-Host Caddy Docker Proxy Implementation Plan

**Status:** In Progress
**Started:** 2025-11-05

## Overview
Extending Caddy setup to support container proxying across multiple Docker hosts using an agent-based architecture with HTTP communication.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Docker Host 1 (Main)                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Caddy Server                                         │  │
│  │  - Admin API enabled (:2019)                         │  │
│  │  - Receives route updates via HTTP POST              │  │
│  │  - Handles all proxying                              │  │
│  │  - caddy-dns/cloudflare + caddy-l4                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ▲                                 │
│                           │ HTTP API                        │
└───────────────────────────┼─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
┌───────────────┼───────┐  ┌───────────┼───────┐
│ Docker Host 2 │       │  │ Docker Host 3     │
│  ┌────────────┴────┐  │  │  ┌────────┴────┐  │
│  │ Caddy Agent     │  │  │  │ Caddy Agent │  │
│  │ (Python)        │  │  │  │ (Python)    │  │
│  │ - Watch Docker  │  │  │  │ - Watch Dkr │  │
│  │ - Read labels   │  │  │  │ - Read lbl  │  │
│  │ - POST to main  │  │  │  │ - POST API  │  │
│  └─────────────────┘  │  │  └──────────────┘  │
└───────────────────────┘  └────────────────────┘
```

## Implementation Tasks

### ✅ Completed
- [x] Research existing solutions and alternatives
- [x] Create implementation plan
- [x] Read and understand existing caddy-agent-watch.py
- [x] Enhance caddy-agent-watch.py with multi-mode support
  - Added agent/server/standalone mode detection
  - Implemented remote Caddy Admin API communication
  - Added host IP auto-detection and manual configuration
  - Added published port mapping for remote containers
  - Added API token authentication support
  - Included agent ID in route metadata for tracking
- [x] Create docker-compose-server.yml - Main Caddy server setup
- [x] Create docker-compose-agent1.yml - Remote agent 1 simulation
- [x] Create docker-compose-agent2.yml - Remote agent 2 simulation
- [x] Create comprehensive documentation
  - Created README-MULTIHOST.md with full architecture
  - Documented all environment variables
  - Added deployment instructions for testing and production
  - Included troubleshooting guide
  - Updated main README.md with reference to multi-host docs

### 🔄 In Progress
- [ ] Testing & Validation

### 📋 Todo
1. **Testing & Validation**
   - Test standalone mode (current behavior)
   - Test server mode with local agent
   - Test with multiple agents
   - Verify cross-host routing
   - Create test script for automated testing

## Key Features

### Agent Modes
- **standalone**: Current behavior - watches local Docker, updates local Caddy
- **server**: Runs Caddy with Admin API, accepts route updates from agents
- **agent**: Watches local Docker, posts routes to remote server

### Environment Variables
- `AGENT_MODE`: standalone|server|agent (default: standalone)
- `AGENT_ID`: Unique identifier for agent (default: hostname)
- `CADDY_SERVER_URL`: URL of main Caddy server (default: http://localhost:2019)
- `CADDY_API_TOKEN`: Bearer token for authentication (optional)
- `HOST_IP`: IP address of agent host for upstream routing (auto-detect if not set)
- `DOCKER_LABEL_PREFIX`: Label prefix to watch (default: caddy)

## Research References

### Solutions Found
1. **caddy-docker-proxy controller mode** - https://github.com/lucaslorentz/caddy-docker-proxy
2. **traefik-kop** (inspiration) - https://github.com/jittering/traefik-kop
3. **Consul/etcd service discovery** - https://www.consul.io/

### Key Documentation
- Caddy Admin API: https://caddyserver.com/docs/api
- Docker Python SDK: https://docker-py.readthedocs.io/
- caddy-docker-proxy README: https://github.com/lucaslorentz/caddy-docker-proxy/blob/master/README.md

## Progress Log

### 2025-11-05 - Implementation Complete
- ✅ Completed research phase
- ✅ Created implementation plan
- ✅ Read and analyzed existing caddy-agent-watch.py
- ✅ Enhanced caddy-agent-watch.py with multi-mode support
  - Added AGENT_MODE, AGENT_ID, and all required environment variables
  - Implemented detect_host_ip() for auto-detection
  - Implemented get_published_port() for port mapping
  - Updated get_caddy_routes() to handle agent/server/standalone modes
  - Updated push_to_caddy() with authentication headers
  - Enhanced merge_routes() to track routes by agent ID
  - Added startup logging to display configuration
- ✅ Created docker-compose-server.yml for main Caddy + agent
- ✅ Created docker-compose-agent1.yml for first remote agent
- ✅ Created docker-compose-agent2.yml for second remote agent
- ✅ Created comprehensive README-MULTIHOST.md documentation
- ✅ Updated main README.md with reference to multi-host feature
- 🔄 Ready for testing phase
