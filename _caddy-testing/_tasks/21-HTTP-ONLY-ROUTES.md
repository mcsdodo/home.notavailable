# HTTP-Only Routes Support

**Date:** 2025-11-28
**Status:** ✅ COMPLETE

## Problem

Agent adds all routes to srv1 (HTTPS server on :443), but `.lan` domains need HTTP-only (srv2 on :80) because:
1. ACME rejects `.lan` TLDs - can't get public certs
2. docker-proxy on small handles `http://*.lan` via srv2

**Current behavior:**
- `caddy: alloy.lan` → srv1 (:443) → Caddy tries TLS cert → fails

**Needed behavior:**
- `caddy: http://alloy.lan` → srv2 (:80) → HTTP-only, no TLS
- `caddy: agent-remote.lacny.me` → srv1 (:443) → HTTPS with TLS

## Server Structure (production)

```
srv0: :2020 (admin proxy)
srv1: :80, :443 (HTTPS with TLS - docker-proxy managed)
srv2: :80 only (HTTP-only - docker-proxy managed for *.lan)
```

## Implementation

### File: `caddy-agent-watch.py`

### Step 1: Parse http:// prefix in label parsing (line ~243)

```python
# In parse_container_labels(), when setting domain:
if not directive:
    # Base label: caddy or caddy_N
    domain_value = label_value
    http_only = False
    if domain_value.startswith('http://'):
        domain_value = domain_value[7:]  # Remove 'http://' prefix
        http_only = True
    route_configs[route_num]['domain'] = domain_value
    route_configs[route_num]['http_only'] = http_only
```

### Step 2: Tag routes with http_only flag (line ~320)

```python
route = {
    "@id": route_id,
    "match": [{"host": domains}],
    "handle": handle,
    "terminal": True,
    "http_only": http_only  # New flag for server selection
}
```

### Step 3: Separate routes by protocol in get_caddy_routes() (line ~158)

```python
def get_caddy_routes():
    # ... existing code ...

    # Separate HTTP-only and HTTPS routes
    http_routes = [r for r in routes if r.pop('http_only', False)]
    https_routes = [r for r in routes if not r.get('http_only')]

    return https_routes, http_routes, global_settings, tls_dns_policies
```

### Step 4: Add routes to correct servers in push_to_caddy()

```python
def push_to_caddy(https_routes, http_routes, global_settings=None, tls_dns_policies=None):
    # ... fetch config ...

    servers = config["apps"]["http"]["servers"]

    # Find HTTPS server (has :443)
    https_server = None
    for name, srv in servers.items():
        listeners = srv.get("listen", [])
        if ":443" in listeners:
            https_server = name
            break

    # Find HTTP-only server (has :80 but NOT :443)
    http_server = None
    for name, srv in servers.items():
        listeners = srv.get("listen", [])
        has_80 = ":80" in listeners or any(":80" in l for l in listeners)
        has_443 = ":443" in listeners or any(":443" in l for l in listeners)
        if has_80 and not has_443:
            http_server = name
            break

    # Add HTTPS routes to srv1
    if https_routes and https_server:
        local_routes = servers[https_server].get("routes", [])
        merged = merge_routes(local_routes, https_routes)
        servers[https_server]["routes"] = merged

    # Add HTTP routes to srv2
    if http_routes and http_server:
        local_routes = servers[http_server].get("routes", [])
        merged = merge_routes(local_routes, http_routes)
        servers[http_server]["routes"] = merged

    # ... push config ...
```

## Testing

1. Deploy to test host (192.168.0.96)
2. Create test containers:
   - `caddy: http://test.lan` → should go to srv2
   - `caddy: test.lacny.me` → should go to srv1
3. Verify routes are in correct servers
4. Test HTTP access to `.lan` domain
5. Test HTTPS access to `.lacny.me` domain

## Test Compose

```yaml
services:
  test-http-only:
    image: hashicorp/http-echo
    command: ["-listen=:80", "-text=HTTP-only route works"]
    ports:
      - "9200:80"
    labels:
      caddy: http://test.lan
      caddy.reverse_proxy: "{{upstreams 80}}"

  test-https:
    image: hashicorp/http-echo
    command: ["-listen=:80", "-text=HTTPS route works"]
    ports:
      - "9201:80"
    labels:
      caddy: test.lacny.me
      caddy.reverse_proxy: "{{upstreams 80}}"
```

## Verification Commands

```bash
# Check srv1 routes (HTTPS)
curl -s http://192.168.0.96:2019/config/apps/http/servers/srv1/routes | python3 -m json.tool | grep -A2 'host'

# Check srv2 routes (HTTP-only)
curl -s http://192.168.0.96:2019/config/apps/http/servers/srv2/routes | python3 -m json.tool | grep -A2 'host'

# Test HTTP-only
curl http://test.lan/

# Test HTTPS
curl https://test.lacny.me/
```

## Test Results

**Agent logs show correct separation:**
```
Processing route 0: domain=httponly.test.lan, http_only=True
Processing route 0: domain=https.test.lan, http_only=False
Server selection: HTTPS=srv1, HTTP-only=srv2
HTTP-only routes: ['http-test_test-http-only']
HTTPS routes: ['http-test_test-https']
```

**Routes in correct servers:**
- srv1 (:443): `https.test.lan` ✅
- srv2 (:80): `httponly.test.lan` ✅

**End-to-end test:**
```
curl -H 'Host: httponly.test.lan' http://localhost:80/
SUCCESS - HTTP-only route (srv2)
```

**Image pushed:** `mcsdodo/caddy-agent:latest`
