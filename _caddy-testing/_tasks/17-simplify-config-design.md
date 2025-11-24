# Simplify Caddy Agent Configuration - Design Document

**Date:** 2025-11-24
**Status:** Ready for implementation

## Overview

Reduce configuration complexity by removing redundant environment variables and simplifying the mode detection logic.

## Goals

- **Reduce operator confusion** - Current `AGENT_MODE` (standalone/server/agent) + separate URL vars is hard to explain
- **Remove dead code** - `standalone` vs `server` mode does the same thing
- **Prepare for future changes** - Cleaner foundation before adding new features

## Configuration Model

### Environment Variables (5 total)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `CADDY_URL` | No | `http://localhost:2019` | Caddy Admin API endpoint |
| `HOST_IP` | No | Auto-detect or None | IP for upstreams; enables remote mode when set |
| `AGENT_ID` | No | hostname | Unique identifier for route tagging |
| `DOCKER_LABEL_PREFIX` | No | `caddy` | Label prefix to watch |
| `CADDY_API_TOKEN` | No | empty | Bearer token for API auth |

### Removed Variables

- `AGENT_MODE` - No longer needed; mode inferred from `HOST_IP`
- `CADDY_API_URL` - Replaced by `CADDY_URL`
- `CADDY_SERVER_URL` - Replaced by `CADDY_URL`

### Mode Detection Logic

```python
CADDY_URL = os.getenv("CADDY_URL", "http://localhost:2019")
HOST_IP = os.getenv("HOST_IP", None)

def get_effective_host_ip():
    """Get HOST_IP for upstreams. Returns None for local mode."""
    if HOST_IP:
        logger.info(f"Using HOST_IP: {HOST_IP} (explicit)")
        return HOST_IP
    if is_host_network_mode():
        detected = detect_host_ip()
        logger.info(f"Using HOST_IP: {detected} (auto-detected, network_mode: host)")
        return detected
    logger.info("Using local addressing (no HOST_IP, container network)")
    return None
```

## Upstream Address Resolution

```
┌─────────────────────────────────────────────────────────────┐
│                  Upstream Resolution Flow                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  HOST_IP set?  ───Yes───►  Use HOST_IP:port                 │
│       │                    (e.g., 192.168.0.98:5678)        │
│       No                                                     │
│       ▼                                                      │
│  network_mode: host?  ───Yes───►  Auto-detect IP            │
│       │                           Log: "Auto-detected..."    │
│       No                          Use detected_ip:port       │
│       ▼                                                      │
│  Use container addressing                                    │
│  (container_name:port or localhost:port)                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Logging for Debugging

```
# When HOST_IP explicitly set:
INFO  Using HOST_IP: 192.168.0.98 (explicit)

# When auto-detected:
INFO  Using HOST_IP: 192.168.0.98 (auto-detected, network_mode: host)

# When local mode:
INFO  Using local addressing (no HOST_IP, container network)
```

### Port Resolution (unchanged)

- `network_mode: host` → use container's internal port directly
- Bridge network → use published host port from Docker inspect

## Docker Compose Changes

### host1 (server - runs Caddy + agent)

```yaml
services:
  caddy-agent:
    environment:
      - CADDY_URL=http://localhost:2019
      - AGENT_ID=host1-server
      - DOCKER_LABEL_PREFIX=caddy
    network_mode: host
    # No HOST_IP = local mode (container names for upstreams)
```

### host2 (remote agent - auto-detect test)

```yaml
services:
  caddy-agent:
    environment:
      - CADDY_URL=http://192.168.0.96:2019
      - AGENT_ID=host2-remote
      - DOCKER_LABEL_PREFIX=caddy
      # HOST_IP not set - will auto-detect with network_mode: host
    network_mode: host
```

### host3 (remote agent - bridge network test)

```yaml
services:
  caddy-agent:
    environment:
      - CADDY_URL=http://192.168.0.96:2019
      - AGENT_ID=host3-remote
      - HOST_IP=192.168.0.99  # Required - can't auto-detect on bridge
      - DOCKER_LABEL_PREFIX=caddy
    # No network_mode: host - uses default bridge

  test-app:
    ports:
      - "9000:9000"  # Must publish ports for bridge network
```

### Test Matrix

| Host | Network Mode | HOST_IP | Expected Behavior |
|------|--------------|---------|-------------------|
| host1 | `host` | Not set | Local mode, container names |
| host2 | `host` | Not set | Auto-detect IP |
| host3 | bridge | Explicit `192.168.0.99` | Use explicit IP + published ports |

## Code Changes

### File: `caddy-agent-watch.py`

**1. Configuration section (lines 14-20):**

```python
# Old
AGENT_MODE = os.getenv("AGENT_MODE", "standalone")
CADDY_API_URL = os.getenv("CADDY_API_URL", "http://caddy:2019")
CADDY_SERVER_URL = os.getenv("CADDY_SERVER_URL", "http://localhost:2019")
HOST_IP = os.getenv("HOST_IP", None)

# New
CADDY_URL = os.getenv("CADDY_URL", "http://localhost:2019")
HOST_IP = os.getenv("HOST_IP", None)
```

**2. Remove `get_target_caddy_url()` function** - just use `CADDY_URL` directly

**3. New `get_effective_host_ip()` function:**

```python
def get_effective_host_ip():
    """Get HOST_IP for upstreams. Returns None for local mode."""
    if HOST_IP:
        logger.info(f"Using HOST_IP: {HOST_IP} (explicit)")
        return HOST_IP
    if is_host_network_mode():
        detected = detect_host_ip()
        logger.info(f"Using HOST_IP: {detected} (auto-detected, network_mode: host)")
        return detected
    logger.info("Using local addressing (no HOST_IP, container network)")
    return None
```

**4. Update all references:**

- `AGENT_MODE == "agent"` → `get_effective_host_ip() is not None`
- `get_target_caddy_url()` → `CADDY_URL`
- Startup logging to show new config format

## Documentation Updates

1. **`_caddy-testing/CLAUDE.md`** - Update environment variables section
2. **`_caddy-testing/docs/CONFIGURATION.md`** - Full reference for new config model
3. **Inline code comments** - Explain auto-detection logic

## Testing Plan

| Test | Method | Validates |
|------|--------|-----------|
| Unit tests | `test_phase*.py` | Label parsing unchanged |
| host1 deploy | Manual | Local mode, container names |
| host2 deploy | Manual | Auto-detect HOST_IP |
| host3 deploy | Manual | Explicit HOST_IP + bridge network |
| Cross-host routing | `curl -H "Host: ..."` | All upstreams reachable |

### Verification Commands

```bash
# Check agent logs for HOST_IP resolution
ssh root@192.168.0.98 "docker logs caddy-agent-remote 2>&1 | grep HOST_IP"

# Verify routes registered correctly
curl -s http://192.168.0.96:2019/config/apps/http/servers/reverse_proxy/routes | jq '.[].handle[].upstreams'
```

## Backward Compatibility

**None** - This is a breaking change. Old env vars (`AGENT_MODE`, `CADDY_API_URL`, `CADDY_SERVER_URL`) will be ignored. The system is not deployed anywhere yet, so no migration needed.
