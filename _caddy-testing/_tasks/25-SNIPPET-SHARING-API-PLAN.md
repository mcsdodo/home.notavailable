# Snippet Sharing API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable remote agents to fetch snippet definitions from host1 via HTTP API.

**Architecture:** Host1 agent serves snippets via HTTP on port 8567. Remote agents fetch snippets on-demand when building routes, with 5-minute caching. No authentication (network isolation).

**Tech Stack:** Python http.server, requests, threading

---

## Task 1: Add Snippet API Server

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py:1-36` (add env vars)
- Modify: `_caddy-testing/caddy-agent-watch.py:1127-1158` (start API server)

**Step 1: Add environment variables after line 26**

After `LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()`, add:

```python
# Snippet sharing API configuration
SNIPPET_API_PORT = int(os.getenv("SNIPPET_API_PORT", "0"))  # 0 = disabled
SNIPPET_SOURCES = os.getenv("SNIPPET_SOURCES", "")  # Comma-separated URLs
SNIPPET_CACHE_TTL = int(os.getenv("SNIPPET_CACHE_TTL", "300"))  # 5 minutes
```

**Step 2: Add snippet cache variables after line 29**

After `_effective_host_ip = None`, add:

```python
# Snippet API cache
_snippet_cache = {}
_snippet_cache_time = 0
```

**Step 3: Add start_snippet_api function before watch_docker_events (around line 1103)**

```python
def start_snippet_api(snippets_ref):
    """Start HTTP server to serve snippets (if enabled)"""
    if SNIPPET_API_PORT <= 0:
        return

    from http.server import HTTPServer, BaseHTTPRequestHandler

    class SnippetHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/snippets":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                # Get current snippets from Docker labels
                _, current_snippets = parse_globals_and_snippets_from_all_containers()
                self.wfile.write(json.dumps(current_snippets).encode())
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            logger.debug(f"Snippet API: {args[0]}")

    server = HTTPServer(("0.0.0.0", SNIPPET_API_PORT), SnippetHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Snippet API listening on :{SNIPPET_API_PORT}")
```

**Step 4: Add helper function to get snippets from all containers**

Add after `parse_globals_and_snippets` function (around line 220):

```python
def parse_globals_and_snippets_from_all_containers():
    """Collect global settings and snippets from all Docker containers"""
    global_settings = {}
    snippets = {}

    for container in client.containers.list():
        labels = container.attrs['Config']['Labels']
        if not labels:
            continue

        # Optional: filter containers by agent filter label
        if AGENT_FILTER_LABEL:
            filter_key, filter_value = AGENT_FILTER_LABEL.split("=", 1) if "=" in AGENT_FILTER_LABEL else (AGENT_FILTER_LABEL, None)
            container_filter_value = labels.get(filter_key)
            if not container_filter_value:
                continue
            if filter_value and container_filter_value != filter_value:
                continue

        container_globals, container_snippets = parse_globals_and_snippets(labels)
        global_settings.update(container_globals)
        snippets.update(container_snippets)

    return global_settings, snippets
```

**Step 5: Start snippet API in main block**

In the main block, after `sync_config()` (around line 1155), add:

```python
    # Start snippet API server (if enabled)
    if SNIPPET_API_PORT > 0:
        start_snippet_api(None)
```

**Step 6: Log snippet API config in startup**

Add to startup logging block (around line 1151):

```python
    logger.info(f"   Snippet API Port: {SNIPPET_API_PORT} (0=disabled)")
    if SNIPPET_SOURCES:
        logger.info(f"   Snippet Sources: {SNIPPET_SOURCES}")
```

**Step 7: Verify changes**

Run: `python -m py_compile _caddy-testing/caddy-agent-watch.py`
Expected: No output (syntax OK)

**Step 8: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "feat: add snippet API server for serving snippets via HTTP"
```

---

## Task 2: Add Snippet API Client (Remote Fetching)

**Files:**
- Modify: `_caddy-testing/caddy-agent-watch.py` (add fetch function and integrate)

**Step 1: Add fetch_remote_snippets function**

Add after `parse_globals_and_snippets_from_all_containers` function:

```python
def fetch_remote_snippets():
    """Fetch snippets from remote sources (with caching)"""
    global _snippet_cache, _snippet_cache_time

    if not SNIPPET_SOURCES:
        return {}

    # Return cached if still valid
    if time.time() - _snippet_cache_time < SNIPPET_CACHE_TTL:
        logger.debug(f"Using cached snippets ({len(_snippet_cache)} snippets)")
        return _snippet_cache

    for source in SNIPPET_SOURCES.split(","):
        source = source.strip()
        if not source:
            continue
        try:
            response = requests.get(f"{source}/snippets", timeout=5)
            if response.ok:
                _snippet_cache = response.json()
                _snippet_cache_time = time.time()
                logger.info(f"Fetched {len(_snippet_cache)} snippets from {source}")
                return _snippet_cache
            else:
                logger.warning(f"Failed to fetch snippets from {source}: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to fetch snippets from {source}: {e}")

    # Return stale cache on failure
    if _snippet_cache:
        logger.warning(f"Using stale snippet cache ({len(_snippet_cache)} snippets)")
    return _snippet_cache
```

**Step 2: Integrate remote snippets in get_caddy_routes**

In `get_caddy_routes()` function, after local snippet discovery (around line 155), add:

Find this block:
```python
    # Log discovered snippets
    if snippets:
        logger.info(f"Discovered {len(snippets)} snippet(s): {list(snippets.keys())}")
```

Replace with:
```python
    # Merge remote snippets (fetched on-demand, cached)
    remote_snippets = fetch_remote_snippets()
    if remote_snippets:
        snippets.update(remote_snippets)
        logger.info(f"Merged {len(remote_snippets)} remote snippet(s)")

    # Log discovered snippets
    if snippets:
        logger.info(f"Total snippets available: {len(snippets)} - {list(snippets.keys())}")
```

**Step 3: Verify changes**

Run: `python -m py_compile _caddy-testing/caddy-agent-watch.py`
Expected: No output (syntax OK)

**Step 4: Commit**

```bash
git add _caddy-testing/caddy-agent-watch.py
git commit -m "feat: add snippet client for fetching remote snippets with caching"
```

---

## Task 3: Update Docker Compose Files

**Files:**
- Modify: `_caddy-testing/docker-compose-prod-server.yml`
- Modify: `_caddy-testing/docker-compose-prod-agent2.yml`

**Step 1: Add SNIPPET_API_PORT to server compose**

In `docker-compose-prod-server.yml`, find `caddy-agent-server` service environment section:

```yaml
    environment:
      - CADDY_URL=http://localhost:2019
      - AGENT_ID=host1-server
      - DOCKER_LABEL_PREFIX=agent
```

Add after `DOCKER_LABEL_PREFIX`:
```yaml
      - SNIPPET_API_PORT=8567
```

**Step 2: Expose port 8567 on caddy-agent-server**

The service uses `network_mode: host`, so no explicit port mapping needed. The port is automatically exposed.

**Step 3: Add SNIPPET_SOURCES to agent2 compose**

In `docker-compose-prod-agent2.yml`, find `caddy-agent` service environment section:

```yaml
    environment:
      - CADDY_URL=http://192.168.0.96:2020
      - AGENT_ID=host2-remote
      - DOCKER_LABEL_PREFIX=caddy
```

Add after `DOCKER_LABEL_PREFIX`:
```yaml
      - SNIPPET_SOURCES=http://192.168.0.96:8567
```

**Step 4: Add test container for remote snippet import**

In `docker-compose-prod-agent2.yml`, add after the last service:

```yaml
  # Test - remote snippet import (fetches 'wildcard' from host1)
  test-remote-snippet:
    image: hashicorp/http-echo
    container_name: test-remote-snippet
    restart: unless-stopped
    network_mode: host
    command:
      - -listen=:9250
      - -text=SUCCESS - Remote snippet import from host1
    labels:
      caddy: remote-snippet-test.lan
      caddy.import: wildcard
      caddy.reverse_proxy: "{{upstreams 9250}}"
```

**Step 5: Commit**

```bash
git add _caddy-testing/docker-compose-prod-server.yml _caddy-testing/docker-compose-prod-agent2.yml
git commit -m "feat: configure snippet API in compose files"
```

---

## Task 4: Add Automated Tests

**Files:**
- Modify: `_caddy-testing/test_all.py`

**Step 1: Add import for json**

At the top of the file, ensure `json` is imported (add if missing):

```python
import json
```

**Step 2: Add SnippetAPITests class**

Add after `ServerModeTests` class (around line 516):

```python
# =============================================================================
# SNIPPET API TESTS
# =============================================================================

class SnippetAPITests:
    """Tests for Snippet Sharing API"""

    @staticmethod
    def test_snippet_api_accessible():
        """Test: Snippet API is accessible on host1"""
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "5", f"http://{CADDY_SERVER}:8567/snippets"],
                capture_output=True, text=True, timeout=7
            )
            assert result.returncode == 0 and result.stdout, f"Snippet API not accessible"
            data = json.loads(result.stdout)
            assert isinstance(data, dict), f"Expected JSON object, got: {type(data)}"
            print("[PASS] test_snippet_api_accessible")
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON response: {e}")

    @staticmethod
    def test_snippet_api_returns_snippets():
        """Test: Snippet API returns expected snippets"""
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "5", f"http://{CADDY_SERVER}:8567/snippets"],
                capture_output=True, text=True, timeout=7
            )
            data = json.loads(result.stdout)
            # Host1 should have at least 'wildcard' and 'internal' snippets
            assert len(data) > 0, f"No snippets returned"
            print(f"[PASS] test_snippet_api_returns_snippets ({len(data)} snippets: {list(data.keys())})")
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON response: {e}")

    @staticmethod
    def test_remote_snippet_import():
        """Test: Remote agent can use snippet fetched from host1"""
        result = IntegrationTests.run_curl("remote-snippet-test.lan", port=443, https=True)
        assert result and "remote" in result.lower(), f"Expected remote-snippet response, got: {result}"
        print("[PASS] test_remote_snippet_import")

    @staticmethod
    def run_all():
        """Run all snippet API tests"""
        print("=" * 60)
        print("SNIPPET API TESTS")
        print("=" * 60)

        # First check if snippet API is accessible
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "3", f"http://{CADDY_SERVER}:8567/snippets"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0 or not result.stdout:
                print(f"[SKIP] Snippet API not accessible at {CADDY_SERVER}:8567")
                print("       Make sure caddy-agent-server has SNIPPET_API_PORT=8567")
                return False
        except Exception:
            print(f"[SKIP] Snippet API not accessible at {CADDY_SERVER}:8567")
            return False

        tests = [
            SnippetAPITests.test_snippet_api_accessible,
            SnippetAPITests.test_snippet_api_returns_snippets,
            SnippetAPITests.test_remote_snippet_import,
        ]

        passed = 0
        failed = 0
        for test in tests:
            try:
                test()
                passed += 1
            except AssertionError as e:
                print(f"[FAIL] {test.__name__}: {e}")
                failed += 1
            except Exception as e:
                print(f"[ERROR] {test.__name__}: {e}")
                failed += 1

        print(f"\nPassed: {passed}/{len(tests)}")
        return failed == 0
```

**Step 3: Add --snippet-api argument**

In the `main()` function, find the argument parser section:

```python
    parser.add_argument("--server-mode", action="store_true", help="Run server mode tests only")
    parser.add_argument("--config", action="store_true", help="Run config tests only")
```

Add after:
```python
    parser.add_argument("--snippet-api", action="store_true", help="Run snippet API tests only")
```

**Step 4: Update run flags**

Find:
```python
    any_specific = args.unit or args.integration or args.server_mode or args.config
```

Replace with:
```python
    any_specific = args.unit or args.integration or args.server_mode or args.config or args.snippet_api
```

**Step 5: Add run_snippet_api variable**

After:
```python
    run_config = args.config or not any_specific
```

Add:
```python
    run_snippet_api = args.snippet_api or not any_specific
```

**Step 6: Add snippet API test execution**

After:
```python
    if run_server_mode:
        results.append(("Server Mode Tests", ServerModeTests.run_all()))
        print()
```

Add:
```python
    if run_snippet_api:
        results.append(("Snippet API Tests", SnippetAPITests.run_all()))
        print()
```

**Step 7: Verify syntax**

Run: `python -m py_compile _caddy-testing/test_all.py`
Expected: No output (syntax OK)

**Step 8: Commit**

```bash
git add _caddy-testing/test_all.py
git commit -m "test: add snippet API tests"
```

---

## Task 5: Update Documentation

**Files:**
- Modify: `_caddy-testing/CLAUDE.md`

**Step 1: Add snippet API section to environment variables**

Find the "Environment Variables" section under "Route Recovery Mechanism". After the existing table, add a new section:

```markdown
### Snippet Sharing API

Share snippet definitions between hosts via HTTP API.

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `SNIPPET_API_PORT` | `0` | Port to serve snippets API. `0` = disabled. |
| `SNIPPET_SOURCES` | `` | Comma-separated URLs to fetch snippets from |
| `SNIPPET_CACHE_TTL` | `300` | Cache duration in seconds (5 min default) |

**Usage:**

Host1 (serves snippets):
```yaml
caddy-agent:
  environment:
    - SNIPPET_API_PORT=8567
```

Host2/Host3 (fetches snippets):
```yaml
caddy-agent:
  environment:
    - SNIPPET_SOURCES=http://192.168.0.96:8567
```

**API Endpoint:**

`GET /snippets` - Returns all discovered snippets as JSON.

**Test snippet API:**
```bash
curl -s http://192.168.0.96:8567/snippets | python -m json.tool
```
```

**Step 2: Commit**

```bash
git add _caddy-testing/CLAUDE.md
git commit -m "docs: add snippet API documentation"
```

---

## Task 6: Deploy and Test

**Step 1: Build new agent image**

```bash
cd _caddy-testing
docker build -t caddy-agent:latest .
docker save caddy-agent:latest | gzip > caddy-agent.tar.gz
```

**Step 2: Deploy to host1**

```bash
scp caddy-agent.tar.gz docker-compose-prod-server.yml root@192.168.0.96:/root/caddy-multihost/
ssh root@192.168.0.96 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-server.yml up -d --force-recreate"
```

**Step 3: Verify snippet API on host1**

```bash
curl -s http://192.168.0.96:8567/snippets | python -m json.tool
```

Expected: JSON with snippets like `wildcard`, `https`, `internal`

**Step 4: Deploy to host2**

```bash
scp caddy-agent.tar.gz docker-compose-prod-agent2.yml root@192.168.0.98:/root/caddy-multihost/
ssh root@192.168.0.98 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-agent2.yml up -d --force-recreate"
```

**Step 5: Verify remote snippet import**

```bash
curl -sk --resolve remote-snippet-test.lan:443:192.168.0.96 https://remote-snippet-test.lan
```

Expected: `SUCCESS - Remote snippet import from host1`

**Step 6: Run automated tests**

```bash
python _caddy-testing/test_all.py --snippet-api
```

Expected: All tests pass

**Step 7: Update task status**

Update `_caddy-testing/_tasks/25-SNIPPET-SHARING-API.md`:
- Change `**Status:** DESIGNED` to `**Status:** IMPLEMENTED`

```bash
git add _caddy-testing/_tasks/25-SNIPPET-SHARING-API.md
git commit -m "docs: mark snippet sharing API as implemented"
```
