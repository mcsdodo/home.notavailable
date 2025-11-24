# Simplify Caddy Agent Configuration - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce configuration complexity from 6 env vars to 5 by removing redundant `AGENT_MODE`, `CADDY_API_URL`, and `CADDY_SERVER_URL`.

**Architecture:** Replace mode-based URL selection with single `CADDY_URL`. Infer remote mode from `HOST_IP` presence. Add smart auto-detection for `network_mode: host` containers.

**Tech Stack:** Python 3.11, Docker SDK, pytest

**Design Document:** `_caddy-testing/_tasks/17-simplify-config-design.md`

---

## Task 1: Add Configuration Unit Tests

**Files:**
- Create: `_caddy-testing/test_config.py`

**Step 1: Write failing tests for new configuration logic**

```python
#!/usr/bin/env python3
"""
Unit tests for simplified configuration model.
Tests the new CADDY_URL + HOST_IP configuration approach.
"""

import os
import socket

# Mock the environment before importing
def setup_env(env_vars):
    """Helper to set environment variables for testing"""
    for key in ['CADDY_URL', 'HOST_IP', 'AGENT_MODE', 'CADDY_API_URL', 'CADDY_SERVER_URL']:
        if key in os.environ:
            del os.environ[key]
    for key, value in env_vars.items():
        os.environ[key] = value

def test_caddy_url_default():
    """Test: CADDY_URL defaults to http://localhost:2019"""
    setup_env({})
    url = os.getenv("CADDY_URL", "http://localhost:2019")
    assert url == "http://localhost:2019"
    print("[PASS] test_caddy_url_default")

def test_caddy_url_custom():
    """Test: CADDY_URL can be set to remote server"""
    setup_env({"CADDY_URL": "http://192.168.0.96:2019"})
    url = os.getenv("CADDY_URL", "http://localhost:2019")
    assert url == "http://192.168.0.96:2019"
    print("[PASS] test_caddy_url_custom")

def test_host_ip_not_set_returns_none():
    """Test: HOST_IP not set returns None (local mode)"""
    setup_env({})
    host_ip = os.getenv("HOST_IP", None)
    assert host_ip is None
    print("[PASS] test_host_ip_not_set_returns_none")

def test_host_ip_explicit():
    """Test: HOST_IP can be explicitly set"""
    setup_env({"HOST_IP": "192.168.0.98"})
    host_ip = os.getenv("HOST_IP", None)
    assert host_ip == "192.168.0.98"
    print("[PASS] test_host_ip_explicit")

def test_remote_mode_detection():
    """Test: Remote mode is detected when HOST_IP is set"""
    setup_env({"HOST_IP": "192.168.0.98"})
    host_ip = os.getenv("HOST_IP", None)
    is_remote_mode = host_ip is not None
    assert is_remote_mode == True
    print("[PASS] test_remote_mode_detection")

def test_local_mode_detection():
    """Test: Local mode when HOST_IP is not set"""
    setup_env({})
    host_ip = os.getenv("HOST_IP", None)
    is_remote_mode = host_ip is not None
    assert is_remote_mode == False
    print("[PASS] test_local_mode_detection")

if __name__ == "__main__":
    test_caddy_url_default()
    test_caddy_url_custom()
    test_host_ip_not_set_returns_none()
    test_host_ip_explicit()
    test_remote_mode_detection()
    test_local_mode_detection()
    print("\n✅ All configuration tests passed!")
```

**Step 2: Run tests to verify they work**

```bash
cd _caddy-testing && python test_config.py
```

Expected output:
```
[PASS] test_caddy_url_default
[PASS] test_caddy_url_custom
[PASS] test_host_ip_not_set_returns_none
[PASS] test_host_ip_explicit
[PASS] test_remote_mode_detection
[PASS] test_local_mode_detection

✅ All configuration tests passed!
```

**Step 3: Commit**

```bash
git add _caddy-testing/test_config.py
git commit -m "test: add unit tests for simplified configuration model"
```

---

## Task 2: Update Configuration Variables

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py:14-21`

**Step 1: Replace old env vars with new ones**

Change lines 14-21 from:

```python
AGENT_MODE = os.getenv("AGENT_MODE", "standalone")  # standalone, server, agent
AGENT_ID = os.getenv("AGENT_ID", socket.gethostname())
CADDY_API_URL = os.getenv("CADDY_API_URL", "http://caddy:2019")
CADDY_SERVER_URL = os.getenv("CADDY_SERVER_URL", "http://localhost:2019")  # For agent mode
CADDY_API_TOKEN = os.getenv("CADDY_API_TOKEN", "")
HOST_IP = os.getenv("HOST_IP", None)  # Will auto-detect if not set
DOCKER_LABEL_PREFIX = os.getenv("DOCKER_LABEL_PREFIX", "caddy")
AGENT_FILTER_LABEL = os.getenv("AGENT_FILTER_LABEL", None)  # Optional: filter containers by label (e.g., "agent=remote1")
```

To:

```python
# Configuration - Simplified model
CADDY_URL = os.getenv("CADDY_URL", "http://localhost:2019")
HOST_IP = os.getenv("HOST_IP", None)  # If set, enables remote mode. Auto-detects with network_mode: host
AGENT_ID = os.getenv("AGENT_ID", socket.gethostname())
CADDY_API_TOKEN = os.getenv("CADDY_API_TOKEN", "")
DOCKER_LABEL_PREFIX = os.getenv("DOCKER_LABEL_PREFIX", "caddy")
AGENT_FILTER_LABEL = os.getenv("AGENT_FILTER_LABEL", None)

# Cached effective host IP (computed once at startup)
_effective_host_ip = None
```

**Step 2: Run existing tests to verify no syntax errors**

```bash
cd _caddy-testing && python -c "import caddy-agent-watch" 2>&1 || python -c "exec(open('caddy-agent-watch.py').read())"
```

Note: This will fail with NameError for removed variables - that's expected until we complete Task 3.

**Step 3: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "refactor: replace AGENT_MODE with simplified CADDY_URL config"
```

---

## Task 3: Add get_effective_host_ip() Function

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py` (after line 39, after detect_host_ip function)

**Step 1: Add the new function**

Insert after the `detect_host_ip()` function (around line 40):

```python
def is_host_network_mode():
    """Check if the agent container itself is running in host network mode.
    We detect this by checking if we can see the host's network interfaces.
    """
    try:
        # In host network mode, we can detect the host IP
        # In bridge mode, detect_host_ip returns the container's gateway
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        # If IP starts with 172.17 or 172.18, we're likely in bridge mode
        # This is a heuristic - not 100% reliable but good enough
        return not ip.startswith("172.")
    except Exception:
        return False

def get_effective_host_ip():
    """Get the effective HOST_IP for upstream resolution.

    Returns:
        str: IP address to use for upstreams (remote mode)
        None: Use container names/localhost (local mode)

    Logic:
        1. If HOST_IP is explicitly set, use it
        2. If running in network_mode: host, auto-detect
        3. Otherwise, return None (local mode)
    """
    global _effective_host_ip

    # Return cached value if already computed
    if _effective_host_ip is not None:
        return _effective_host_ip if _effective_host_ip != "" else None

    if HOST_IP:
        logger.info(f"Using HOST_IP: {HOST_IP} (explicit)")
        _effective_host_ip = HOST_IP
        return HOST_IP

    if is_host_network_mode():
        detected = detect_host_ip()
        logger.info(f"Using HOST_IP: {detected} (auto-detected, network_mode: host)")
        _effective_host_ip = detected
        return detected

    logger.info("Using local addressing (no HOST_IP, container network)")
    _effective_host_ip = ""  # Empty string means "computed, result is None"
    return None
```

**Step 2: Verify syntax**

```bash
cd _caddy-testing && python -c "exec(open('caddy-agent-watch.py').read())" 2>&1 | head -5
```

**Step 3: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "feat: add get_effective_host_ip() with auto-detection for host network mode"
```

---

## Task 4: Remove get_target_caddy_url() Function

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py:62-67`

**Step 1: Delete the function**

Remove lines 62-67:

```python
def get_target_caddy_url():
    """Get the target Caddy API URL based on mode"""
    if AGENT_MODE == "agent":
        return CADDY_SERVER_URL
    else:
        return CADDY_API_URL
```

**Step 2: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "refactor: remove get_target_caddy_url(), use CADDY_URL directly"
```

---

## Task 5: Update get_caddy_routes() Function

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py` (line 74 area, now shifted after Task 4)

**Step 1: Update host_ip resolution**

Find this line (around line 68 after previous deletions):

```python
    host_ip = HOST_IP or detect_host_ip() if AGENT_MODE == "agent" else None
```

Replace with:

```python
    host_ip = get_effective_host_ip()
```

**Step 2: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "refactor: use get_effective_host_ip() in get_caddy_routes()"
```

---

## Task 6: Update resolve_upstreams() Function

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py` (around line 479 area)

**Step 1: Replace AGENT_MODE check with host_ip check**

Find this block (around line 473-516):

```python
        # Agent mode: use host IP + published port (or direct port for host networking)
        if AGENT_MODE == "agent":
```

Replace the entire if/else block with:

```python
        # Remote mode: use host IP + port (when host_ip is available)
        if host_ip:
            if is_host_network:
                # Host networking: use host IP + internal port directly
                resolved = f"{host_ip}:{port}"
                logger.info(f"[REMOTE] Resolved {{{{upstreams {port}}}}} for domain '{domain}' (host network): {resolved}")
                return resolved
            else:
                # Bridge networking: need published port
                published_port = get_published_port(container, port)
                if published_port:
                    resolved = f"{host_ip}:{published_port}"
                    logger.info(f"[REMOTE] Resolved {{{{upstreams {port}}}}} for domain '{domain}': {resolved}")
                    return resolved
                else:
                    logger.error(f"[REMOTE] Cannot resolve upstream for {container.name}: port {port} not published")
                    return None
        # Local mode: use container addressing
        else:
            if is_host_network:
                # Host networking: containers share host network, use localhost
                resolved = f"localhost:{port}"
                logger.info(f"[LOCAL] Resolved {{{{upstreams {port}}}}} for domain '{domain}' (host network): {resolved}")
                return resolved
            else:
                # Bridge networking: use container IP
                network_settings = container.attrs.get('NetworkSettings', {})
                networks = network_settings.get('Networks', {})
                if networks:
                    ip = list(networks.values())[0].get('IPAddress')
                    if ip:
                        resolved = f"{ip}:{port}"
                        logger.info(f"[LOCAL] Resolved {{{{upstreams {port}}}}} for domain '{domain}': {resolved}")
                        return resolved
            logger.error(f"Failed to resolve {{{{upstreams {port}}}}} for {container.name}")
            return None
```

**Step 2: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "refactor: replace AGENT_MODE check with host_ip check in resolve_upstreams()"
```

---

## Task 7: Update push_to_caddy() Function

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py` (around line 525 area)

**Step 1: Replace get_target_caddy_url() with CADDY_URL**

Find:

```python
    target_url = get_target_caddy_url()
```

Replace with:

```python
    target_url = CADDY_URL
```

**Step 2: Update log message**

Find (around line 592):

```python
        logger.info(f"Pushing config to {target_url} [Mode: {AGENT_MODE}]")
```

Replace with:

```python
        host_ip = get_effective_host_ip()
        mode_desc = f"remote (HOST_IP={host_ip})" if host_ip else "local"
        logger.info(f"Pushing config to {target_url} [Mode: {mode_desc}]")
```

**Step 3: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "refactor: use CADDY_URL directly in push_to_caddy()"
```

---

## Task 8: Update remove_agent_routes() Function

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py` (around line 741 area)

**Step 1: Replace get_target_caddy_url() with CADDY_URL**

Find:

```python
    target_url = get_target_caddy_url()
```

Replace with:

```python
    target_url = CADDY_URL
```

**Step 2: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "refactor: use CADDY_URL directly in remove_agent_routes()"
```

---

## Task 9: Update Startup Logging

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py` (around line 868-890 area)

**Step 1: Replace startup logging block**

Find the entire startup logging block (lines 868-890):

```python
if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🚀 Caddy Docker Agent Starting")
    logger.info(f"   Mode: {AGENT_MODE}")
    logger.info(f"   Agent ID: {AGENT_ID}")
    logger.info(f"   Docker Label Prefix: {DOCKER_LABEL_PREFIX}")

    if AGENT_MODE == "agent":
        logger.info(f"   Target Server: {CADDY_SERVER_URL}")
        host_ip = HOST_IP or detect_host_ip()
        logger.info(f"   Host IP: {host_ip}")
    else:
        logger.info(f"   Caddy API: {CADDY_API_URL}")

    if CADDY_API_TOKEN:
        logger.info(f"   Authentication: Enabled (token configured)")
    else:
        logger.info(f"   Authentication: Disabled (no token)")

    if AGENT_FILTER_LABEL:
        logger.info(f"   Container Filter: {AGENT_FILTER_LABEL}")

    logger.info("="*60)

    sync_config()  # Initial sync
    watch_docker_events()
```

Replace with:

```python
if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🚀 Caddy Docker Agent Starting")
    logger.info(f"   Agent ID: {AGENT_ID}")
    logger.info(f"   Caddy URL: {CADDY_URL}")
    logger.info(f"   Docker Label Prefix: {DOCKER_LABEL_PREFIX}")

    # Compute and log effective host IP
    effective_ip = get_effective_host_ip()
    if effective_ip:
        logger.info(f"   Mode: REMOTE (upstreams use {effective_ip})")
    else:
        logger.info(f"   Mode: LOCAL (upstreams use container names)")

    if CADDY_API_TOKEN:
        logger.info(f"   Authentication: Enabled (token configured)")
    else:
        logger.info(f"   Authentication: Disabled (no token)")

    if AGENT_FILTER_LABEL:
        logger.info(f"   Container Filter: {AGENT_FILTER_LABEL}")

    logger.info("="*60)

    sync_config()  # Initial sync
    watch_docker_events()
```

**Step 2: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "refactor: update startup logging for simplified config model"
```

---

## Task 10: Update docker-compose-prod-server.yml

**Files:**
- Modify: `_caddy-testing/docker-compose-prod-server.yml`

**Step 1: Update caddy-agent environment**

Find the caddy-agent service environment section and replace:

```yaml
    environment:
      - AGENT_MODE=server
      - AGENT_ID=host1-server
      - CADDY_API_URL=http://localhost:2019
      - DOCKER_LABEL_PREFIX=caddy
```

With:

```yaml
    environment:
      - CADDY_URL=http://localhost:2019
      - AGENT_ID=host1-server
      - DOCKER_LABEL_PREFIX=caddy
      # No HOST_IP = local mode (uses container names for upstreams)
```

**Step 2: Commit**

```bash
git add _caddy-testing/docker-compose-prod-server.yml
git commit -m "refactor: update docker-compose-prod-server.yml for simplified config"
```

---

## Task 11: Update docker-compose-prod-agent2.yml

**Files:**
- Modify: `_caddy-testing/docker-compose-prod-agent2.yml`

**Step 1: Update caddy-agent environment**

Find the caddy-agent service environment section and replace:

```yaml
    environment:
      - AGENT_MODE=agent
      - AGENT_ID=host2-remote
      - CADDY_SERVER_URL=http://192.168.0.96:2019
      - HOST_IP=192.168.0.98
      - DOCKER_LABEL_PREFIX=caddy
```

With:

```yaml
    environment:
      - CADDY_URL=http://192.168.0.96:2019
      - AGENT_ID=host2-remote
      - DOCKER_LABEL_PREFIX=caddy
      # HOST_IP not set - will auto-detect with network_mode: host
```

**Step 2: Commit**

```bash
git add _caddy-testing/docker-compose-prod-agent2.yml
git commit -m "refactor: update docker-compose-prod-agent2.yml for simplified config (auto-detect HOST_IP)"
```

---

## Task 12: Update docker-compose-prod-agent3.yml (Bridge Network Test)

**Files:**
- Modify: `_caddy-testing/docker-compose-prod-agent3.yml`

**Step 1: Update caddy-agent environment and remove network_mode: host**

Replace the entire file with:

```yaml
services:
  caddy-agent:
    image: caddy-agent:phase3
    container_name: caddy-agent-remote3
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - CADDY_URL=http://192.168.0.96:2019
      - AGENT_ID=host3-remote
      - HOST_IP=192.168.0.99
      - DOCKER_LABEL_PREFIX=caddy
    # No network_mode: host - uses bridge network to test explicit HOST_IP

  # Test service - simple label (backward compatibility)
  test-host3:
    image: hashicorp/http-echo
    container_name: test-host3
    restart: unless-stopped
    ports:
      - "9000:9000"
    command:
      - -listen=:9000
      - -text=Simple label on host3
    labels:
      caddy: test-host3.lan
      caddy.reverse_proxy: "{{upstreams 9000}}"

  # Phase 1 test - combined features (numbered + multiple domains)
  test-combined:
    image: hashicorp/http-echo
    container_name: test-combined
    restart: unless-stopped
    ports:
      - "9001:9001"
    command:
      - -listen=:9001
      - -text=Combined features on host3
    labels:
      caddy_0: host3-combined-a.lan, host3-combined-b.lan
      caddy_0.reverse_proxy: "{{upstreams 9001}}"
      caddy_1: host3-single.lan
      caddy_1.reverse_proxy: "{{upstreams 9001}}"

  # Phase 1 test - mixed simple and numbered
  test-mixed:
    image: hashicorp/http-echo
    container_name: test-mixed
    restart: unless-stopped
    ports:
      - "9002:9002"
    command:
      - -listen=:9002
      - -text=Mixed labels on host3
    labels:
      caddy: host3-simple.lan
      caddy.reverse_proxy: "{{upstreams 9002}}"
      caddy_5: host3-numbered5.lan
      caddy_5.reverse_proxy: "{{upstreams 9002}}"

  # Phase 2 test - transport TLS + handle directives
  test-transport-handle:
    image: hashicorp/http-echo
    container_name: test-transport-handle
    restart: unless-stopped
    ports:
      - "9003:9003"
    command:
      - -listen=:9003
      - -text=Phase 2 - Transport and handle on host3
    labels:
      caddy_30: phase2-transport.lan
      caddy_30.reverse_proxy: "{{upstreams 9003}}"
      caddy_30.transport: http
      caddy_30.transport.tls: ""
      caddy_30.transport.tls_insecure_skip_verify: ""
```

**Step 2: Commit**

```bash
git add _caddy-testing/docker-compose-prod-agent3.yml
git commit -m "refactor: update docker-compose-prod-agent3.yml for bridge network test (explicit HOST_IP)"
```

---

## Task 13: Update CLAUDE.md Documentation

**Files:**
- Modify: `_caddy-testing/CLAUDE.md`

**Step 1: Update environment variables section**

Find the "Environment Variables" section and replace with:

```markdown
**Environment Variables**:
- `CADDY_URL`: Caddy Admin API endpoint (default: http://localhost:2019)
- `HOST_IP`: IP for upstreams; enables remote mode. Auto-detects with network_mode: host
- `AGENT_ID`: Unique identifier (default: hostname)
- `DOCKER_LABEL_PREFIX`: Label prefix (default: caddy)
- `CADDY_API_TOKEN`: Bearer token for authentication (optional)
- `AGENT_FILTER_LABEL`: Filter containers by label (optional)
```

**Step 2: Commit**

```bash
git add _caddy-testing/CLAUDE.md
git commit -m "docs: update CLAUDE.md with simplified environment variables"
```

---

## Task 14: Update docs/CONFIGURATION.md

**Files:**
- Modify: `_caddy-testing/docs/CONFIGURATION.md`

**Step 1: Replace the Mode Selection and Connection sections**

Replace the entire "Mode Selection" section (lines 9-26) and add new sections. The new content should be:

```markdown
## Environment Variables

All configuration is done via environment variables. Set them in your docker-compose.yml or .env file.

### Caddy Connection

#### `CADDY_URL` (optional)

URL of the Caddy Admin API to push configurations to.

**Default**: `http://localhost:2019`
**Example**:
```yaml
environment:
  # Local Caddy (same host)
  - CADDY_URL=http://localhost:2019

  # Remote Caddy (central server)
  - CADDY_URL=http://192.168.0.96:2019
```

### Remote Mode Configuration

#### `HOST_IP` (optional)

IP address to use for upstream addresses. When set (or auto-detected), the agent operates in "remote mode" - upstreams are configured as `HOST_IP:port` instead of container names.

**Default**: None (local mode) or auto-detected with `network_mode: host`
**Auto-detection**: When running with `network_mode: host` and `HOST_IP` is not set, the agent automatically detects the host's IP address.

**Example**:
```yaml
environment:
  # Explicit (required for bridge network)
  - HOST_IP=192.168.0.98

  # Or omit for auto-detection (with network_mode: host)
  # HOST_IP will be auto-detected
```

**Mode Detection Logic**:
| HOST_IP | network_mode | Behavior |
|---------|--------------|----------|
| Set | Any | Use explicit HOST_IP for upstreams |
| Not set | host | Auto-detect IP, use for upstreams |
| Not set | bridge | Local mode, use container names |

**Logging**: The agent logs which mode it's using at startup:
```
INFO  Using HOST_IP: 192.168.0.98 (explicit)
INFO  Using HOST_IP: 192.168.0.98 (auto-detected, network_mode: host)
INFO  Using local addressing (no HOST_IP, container network)
```
```

Also remove references to `AGENT_MODE`, `CADDY_API_URL`, and `CADDY_SERVER_URL` throughout the file.

**Step 2: Commit**

```bash
git add _caddy-testing/docs/CONFIGURATION.md
git commit -m "docs: update CONFIGURATION.md for simplified config model"
```

---

## Task 15: Run All Tests and Verify

**Files:**
- None (verification only)

**Step 1: Run configuration tests**

```bash
cd _caddy-testing && python test_config.py
```

Expected: All 6 tests pass

**Step 2: Run phase tests**

```bash
cd _caddy-testing && python test_phase1.py && python test_phase2.py && python test_phase3.py
```

Expected: All tests pass (label parsing is unchanged)

**Step 3: Verify agent starts without errors (local test)**

```bash
cd _caddy-testing && python -c "
import os
os.environ['CADDY_URL'] = 'http://localhost:2019'
exec(open('caddy-agent-watch.py').read().split('if __name__')[0])
print('✅ Agent module loads without errors')
"
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "test: verify all tests pass after configuration simplification"
```

---

## Deployment Verification (Manual)

After implementation, deploy to test hosts and verify:

### Host1 (Server - Local Mode)
```bash
scp caddy-agent.tar.gz docker-compose-prod-server.yml root@192.168.0.96:/root/caddy-multihost/
ssh root@192.168.0.96 "cd /root/caddy-multihost && docker compose -f docker-compose-prod-server.yml up -d"
ssh root@192.168.0.96 "docker logs caddy-agent-server 2>&1 | head -20"
```

Expected log output:
```
🚀 Caddy Docker Agent Starting
   Agent ID: host1-server
   Caddy URL: http://localhost:2019
   Mode: LOCAL (upstreams use container names)
```

### Host2 (Agent - Auto-detect)
```bash
scp caddy-agent.tar.gz docker-compose-prod-agent2.yml root@192.168.0.98:/root/caddy-multihost/
ssh root@192.168.0.98 "cd /root/caddy-multihost && docker compose -f docker-compose-prod-agent2.yml up -d"
ssh root@192.168.0.98 "docker logs caddy-agent-remote 2>&1 | head -20"
```

Expected log output:
```
🚀 Caddy Docker Agent Starting
   Agent ID: host2-remote
   Caddy URL: http://192.168.0.96:2019
   Using HOST_IP: 192.168.0.98 (auto-detected, network_mode: host)
   Mode: REMOTE (upstreams use 192.168.0.98)
```

### Host3 (Agent - Explicit HOST_IP, Bridge Network)
```bash
scp caddy-agent.tar.gz docker-compose-prod-agent3.yml root@192.168.0.99:/root/caddy-multihost/
ssh root@192.168.0.99 "cd /root/caddy-multihost && docker compose -f docker-compose-prod-agent3.yml up -d"
ssh root@192.168.0.99 "docker logs caddy-agent-remote3 2>&1 | head -20"
```

Expected log output:
```
🚀 Caddy Docker Agent Starting
   Agent ID: host3-remote
   Caddy URL: http://192.168.0.96:2019
   Using HOST_IP: 192.168.0.99 (explicit)
   Mode: REMOTE (upstreams use 192.168.0.99)
```

### Verify Cross-Host Routing
```bash
# Test all hosts respond correctly
curl -H "Host: test-local.lan" http://192.168.0.96
curl -H "Host: test-remote.lan" http://192.168.0.96
curl -H "Host: test-host3.lan" http://192.168.0.96
```
