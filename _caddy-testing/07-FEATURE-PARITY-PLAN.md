# Feature Parity Plan: caddy-docker-proxy → caddy-agent

Comprehensive plan to achieve feature parity with lucaslorentz/caddy-docker-proxy.

## Current Usage Analysis

### Features Currently Used

From analysis of all portainer.stacks compose files:

#### 1. **Numbered Labels** (Critical)
```yaml
caddy_0: domain1.com
caddy_1: domain2.com
caddy_10: "*.lacny.me"
```
- Used for: Multiple independent site blocks on same container
- Used in: caddy/docker-compose-small.yml, arr/docker-compose.yml
- **Priority**: HIGH

#### 2. **Multiple Domains** (Critical)
```yaml
caddy_0: http://series.lan, http://sonarr.lan
```
- Used for: Multiple domains pointing to same service
- Used in: arr/docker-compose.yml (sonarr, radarr, overseerr)
- **Priority**: HIGH

#### 3. **{{upstreams PORT}} Template** (Critical)
```yaml
caddy.reverse_proxy: "{{upstreams 80}}"
caddy.reverse_proxy: "{{upstreams 8096}}"
```
- Used for: Auto-discovery of container port
- Used in: Nearly all stacks
- **Priority**: HIGH - Already implemented ✅

#### 4. **Global Settings** (High)
```yaml
caddy_0.email: "email@example.com"
caddy_0.auto_https: prefer_wildcard
```
- Used for: Let's Encrypt email, HTTPS settings
- Used in: caddy/docker-compose-small.yml
- **Priority**: HIGH

#### 5. **Snippets** (High)
```yaml
caddy_1: (wildcard)
caddy_1.tls.dns: "cloudflare ${CF_API_TOKEN}"
caddy_10: "*.lacny.me"
caddy_10.import: wildcard
```
- Used for: Reusable configuration blocks
- Used in: caddy/docker-compose-small.yml for wildcard certs
- **Priority**: HIGH

#### 6. **TLS Configuration** (High)
```yaml
caddy_1.tls.dns: "cloudflare {env.CF_API_TOKEN}"
caddy_1.tls.resolvers: 1.1.1.1 1.0.0.1
caddy_3.transport.tls_insecure_skip_verify: ""
```
- Used for: DNS challenge, custom resolvers, TLS settings
- Used in: caddy/docker-compose-small.yml
- **Priority**: HIGH

#### 7. **Header Manipulation** (Medium)
```yaml
caddy.reverse_proxy.header_up: -X-Forwarded-For
```
- Used for: Removing/adding headers
- Used in: caddy/docker-compose-big-media.yml
- **Priority**: MEDIUM

#### 8. **Environment Variable Injection** (Low)
```yaml
caddy_0.email: "${EMAIL}"
caddy_1.tls.dns: "cloudflare ${CF_API_TOKEN}"
```
- Used for: Template variables in labels
- Used in: caddy/docker-compose-small.yml
- **Priority**: LOW - Handled by Docker Compose

#### 9. **CADDY_INGRESS_NETWORKS** (Medium)
```yaml
environment:
  - CADDY_INGRESS_NETWORKS=caddy
```
- Used for: Only discover containers on specific network
- Used in: All caddy compose files
- **Priority**: MEDIUM

## Implementation Phases

### Phase 1: Critical Features (Week 1)

#### 1.1 Numbered Label Support
**Goal**: Support `caddy_N` suffix for multiple site blocks

**Current**:
```python
domain = labels.get(f"{DOCKER_LABEL_PREFIX}")
proxy_target = labels.get(f"{DOCKER_LABEL_PREFIX}.reverse_proxy")
```

**Needed**:
```python
# Collect all numbered labels
routes = {}
for label_key in labels:
    if label_key.startswith(f"{DOCKER_LABEL_PREFIX}_"):
        # Extract: caddy_0, caddy_1, etc.
        match = re.match(f"{DOCKER_LABEL_PREFIX}_(\d+)(?:\.(.+))?", label_key)
        if match:
            route_num = match.group(1)
            directive = match.group(2) or ""  # Empty for base domain

            if route_num not in routes:
                routes[route_num] = {}

            if not directive:
                # caddy_0: domain.com
                routes[route_num]['domain'] = labels[label_key]
            else:
                # caddy_0.reverse_proxy: upstream
                routes[route_num][directive] = labels[label_key]

# Generate route for each numbered label
for route_num, route_config in sorted(routes.items()):
    domain = route_config.get('domain')
    reverse_proxy = route_config.get('reverse_proxy')
    # ... generate route
```

**Test Case**:
```yaml
labels:
  caddy_0: domain1.com
  caddy_0.reverse_proxy: "{{upstreams 80}}"
  caddy_1: domain2.com
  caddy_1.reverse_proxy: "{{upstreams 8080}}"
```

Expected: 2 separate routes

---

#### 1.2 Multiple Domains per Route
**Goal**: Support comma-separated domains

**Current**:
```python
"match": [{
    "host": [domain]
}]
```

**Needed**:
```python
# Split comma-separated domains
domains = [d.strip() for d in domain.split(',')]

"match": [{
    "host": domains
}]
```

**Test Case**:
```yaml
caddy: http://series.lan, http://sonarr.lan
caddy.reverse_proxy: "{{upstreams 8989}}"
```

Expected: 1 route matching both domains

---

### Phase 2: High Priority Features (Week 2)

#### 2.1 Global Settings Support
**Goal**: Support global Caddy configuration

**Implementation**:
```python
def parse_global_settings(labels):
    """Extract global settings from labels without domain."""
    globals = {}

    for label_key, label_value in labels.items():
        # Match: caddy_N.directive (without domain set)
        match = re.match(f"{DOCKER_LABEL_PREFIX}_(\d+)\.(.+)", label_key)
        if match and not has_domain_label(labels, match.group(1)):
            directive = match.group(2)
            globals[directive] = label_value

    return globals

def generate_caddy_config(containers):
    config = {
        "admin": {"listen": "0.0.0.0:2019"},
        "apps": {
            "http": {
                "servers": {
                    "reverse_proxy": {
                        "listen": [":80"]
                    }
                }
            }
        }
    }

    # Apply global settings
    for container in containers:
        globals = parse_global_settings(container.labels)
        if 'email' in globals:
            config['apps']['http']['servers']['reverse_proxy']['tls'] = {
                "email": globals['email']
            }
        # ... other globals

    return config
```

**Test Case**:
```yaml
labels:
  caddy_0.email: "test@example.com"
  caddy_0.auto_https: prefer_wildcard
```

Expected: Global config with email set

---

#### 2.2 Snippets & Import
**Goal**: Support named snippets and imports

**Implementation**:
```python
def parse_snippets(all_containers):
    """Extract all snippet definitions."""
    snippets = {}

    for container in all_containers:
        for label_key, label_value in container.labels.items():
            # Match: caddy_N: (snippet_name)
            match = re.match(f"{DOCKER_LABEL_PREFIX}_(\d+)", label_key)
            if match and label_value.startswith('(') and label_value.endswith(')'):
                snippet_name = label_value[1:-1]
                route_num = match.group(1)

                # Extract snippet directives
                snippet_config = {}
                for key, value in container.labels.items():
                    if key.startswith(f"{DOCKER_LABEL_PREFIX}_{route_num}."):
                        directive = key.split('.', 1)[1]
                        snippet_config[directive] = value

                snippets[snippet_name] = snippet_config

    return snippets

def apply_imports(route_config, snippets):
    """Apply imported snippets to route."""
    if 'import' in route_config:
        snippet_name = route_config['import']
        if snippet_name in snippets:
            # Merge snippet config into route
            route_config.update(snippets[snippet_name])

    return route_config
```

**Test Case**:
```yaml
# Container 1: Define snippet
labels:
  caddy_1: (wildcard)
  caddy_1.tls.dns: "cloudflare {env.CF_API_TOKEN}"

# Container 2: Use snippet
labels:
  caddy_10: "*.lacny.me"
  caddy_10.import: wildcard
```

Expected: Container 2 gets TLS DNS config from snippet

---

#### 2.3 TLS Directive Support
**Goal**: Support TLS DNS challenge and custom resolvers

**Implementation**:
```python
def parse_tls_config(route_config):
    """Extract TLS configuration from route."""
    tls_config = {}

    for key, value in route_config.items():
        if key.startswith('tls.'):
            directive = key[4:]  # Remove 'tls.' prefix

            if directive == 'dns':
                # Parse: "cloudflare {env.TOKEN}"
                tls_config['automation'] = {
                    'policies': [{
                        'issuers': [{
                            'module': 'dns.providers.' + value.split()[0],
                            'api_token': '{env.' + value.split('{env.')[1].split('}')[0] + '}'
                        }]
                    }]
                }
            elif directive == 'resolvers':
                tls_config['dns_resolvers'] = value.split()

    return tls_config
```

**Test Case**:
```yaml
caddy_1.tls.dns: "cloudflare {env.CF_API_TOKEN}"
caddy_1.tls.resolvers: 1.1.1.1 1.0.0.1
```

Expected: TLS config with DNS challenge and resolvers

---

### Phase 3: Medium Priority Features (Week 3)

#### 3.1 Header Manipulation
**Goal**: Support header_up, header_down directives

**Implementation**:
```python
def parse_headers(route_config):
    """Extract header manipulation directives."""
    headers = []

    for key, value in route_config.items():
        if key.startswith('reverse_proxy.header_up'):
            # Parse: -X-Forwarded-For (remove header)
            if value.startswith('-'):
                headers.append({
                    'delete': [value[1:]]
                })
            else:
                # Parse: +X-Custom "value" (add header)
                headers.append({
                    'set': {value.split()[0]: value.split()[1]}
                })

    return headers

# In route generation:
route['handle'][0]['header_up'] = parse_headers(route_config)
```

**Test Case**:
```yaml
caddy.reverse_proxy.header_up: -X-Forwarded-For
```

Expected: Remove X-Forwarded-For header

---

#### 3.2 Transport Settings
**Goal**: Support TLS transport configuration

**Implementation**:
```python
def parse_transport(route_config):
    """Extract transport configuration."""
    transport = {}

    for key, value in route_config.items():
        if key.startswith('transport.'):
            directive = key[10:]  # Remove 'transport.' prefix

            if directive == 'tls_insecure_skip_verify':
                transport['tls'] = {
                    'insecure_skip_verify': True
                }

    return transport

# In route generation:
if transport := parse_transport(route_config):
    route['handle'][0]['transport'] = transport
```

**Test Case**:
```yaml
caddy_3.transport.tls_insecure_skip_verify: ""
```

Expected: Skip TLS verification for backend

---

### Phase 4: Advanced Features (Week 4) - optional / not used here

#### 4.1 Named Matchers
**Goal**: Support @ matcher syntax

**Implementation**:
```python
def parse_matchers(route_config):
    """Extract named matchers."""
    matchers = {}

    for key, value in route_config.items():
        if key.startswith('@'):
            matcher_name = key.split('.')[0]
            directive = key.split('.', 1)[1] if '.' in key else 'match'

            if matcher_name not in matchers:
                matchers[matcher_name] = {}

            matchers[matcher_name][directive] = value

    return matchers
```

**Test Case**:
```yaml
caddy.@api.path: /api/*
caddy.reverse_proxy: @api backend:8080
```

Expected: Reverse proxy with path matcher

---

#### 4.2 Handle & Handle_Path
**Goal**: Support handle directives

**Implementation**:
```python
def parse_handle(route_config):
    """Extract handle directives."""
    handles = []

    for key, value in route_config.items():
        if key.startswith('handle_path.'):
            path = key.split('.')[1] if len(key.split('.')) > 1 else '*'

            handles.append({
                'match': [{
                    'path': [path]
                }],
                'handle': parse_directives(route_config, f'handle_path.{path}')
            })

    return handles
```

**Test Case**:
```yaml
caddy.handle_path: /api/*
caddy.handle_path.0_reverse_proxy: backend:8080
```

Expected: Path-specific handler

---

## Implementation Checklist

### Phase 1: Critical (Week 1)
- [ ] Numbered label support (`caddy_0`, `caddy_1`)
- [ ] Multiple domains per route (comma-separated)
- [ ] Unit tests for numbered labels
- [ ] Integration tests with multi-domain routes

### Phase 2: High Priority (Week 2)
- [ ] Global settings support
- [ ] Snippet definitions
- [ ] Import directive
- [ ] TLS DNS challenge configuration
- [ ] TLS resolvers
- [ ] Tests for snippets and TLS

### Phase 3: Medium Priority (Week 3)
- [ ] Header manipulation (header_up, header_down)
- [ ] Transport TLS settings
- [ ] Tests for network filtering and headers

### Phase 4: Advanced (Week 4)
- [ ] Named matchers (@matcher syntax)
- [ ] Handle and handle_path directives
- [ ] Rewrite directive
- [ ] Redirect directive
- [ ] Tests for advanced directives

## Compatibility Matrix

| Feature | caddy-docker-proxy | Our Agent | Priority |
|---------|-------------------|-----------|----------|
| Basic reverse_proxy | ✅ | ✅ | - |
| {{upstreams PORT}} | ✅ | ✅ | - |
| Numbered labels | ✅ | ⏳ | HIGH |
| Multiple domains | ✅ | ⏳ | HIGH |
| Global settings | ✅ | ⏳ | HIGH |
| Snippets | ✅ | ⏳ | HIGH |
| TLS DNS | ✅ | ⏳ | HIGH |
| CADDY_INGRESS_NETWORKS | ✅ | ⏳ | MEDIUM |
| Header manipulation | ✅ | ⏳ | MEDIUM |
| Transport settings | ✅ | ⏳ | MEDIUM |
| Named matchers | ✅ | ⏳ | LOW |
| Handle directives | ✅ | ⏳ | LOW |

## Migration Path

### Step 1: Backward Compatibility
- Maintain support for existing simple labels
- Add numbered label support alongside

### Step 2: Gradual Migration
- Test Phase 1 features on non-critical services
- Validate snippet support on caddy-config container
- Migrate TLS configuration

### Step 3: Full Feature Parity
- Enable all caddy-docker-proxy features
- Drop-in replacement ready

## Testing Strategy

### Unit Tests
```python
def test_numbered_labels():
    labels = {
        "caddy_0": "domain1.com",
        "caddy_0.reverse_proxy": "{{upstreams 80}}",
        "caddy_1": "domain2.com",
        "caddy_1.reverse_proxy": "{{upstreams 8080}}"
    }
    routes = parse_numbered_labels(labels)
    assert len(routes) == 2
    assert routes[0]['domain'] == 'domain1.com'
```

### Integration Tests
```bash
# Test multiple domains
docker run -d \
  --label caddy_0="http://test1.lan, http://test2.lan" \
  --label caddy_0.reverse_proxy="{{upstreams 80}}" \
  testapp

# Verify both domains route correctly
curl -H "Host: test1.lan" http://localhost
curl -H "Host: test2.lan" http://localhost
```

### Regression Tests
- Run existing test suite after each phase
- Ensure backward compatibility
- Verify no route conflicts

## Documentation Updates

- [ ] Update README.md with numbered label syntax
- [ ] Add MIGRATION.md for caddy-docker-proxy users
- [ ] Update CONFIGURATION.md with all new directives
- [ ] Create SNIPPETS.md guide
- [ ] Update examples with real-world configs

## Risk Assessment

### High Risk
- Numbered labels: Complex parsing, potential conflicts
- Mitigation: Extensive unit tests, gradual rollout

### Medium Risk
- Snippets: Cross-container dependencies
- Mitigation: Clear snippet resolution order

### Low Risk
- Header manipulation: Well-defined syntax
- Mitigation: Standard Caddy directive mapping

## Success Criteria

✅ All features from portainer.stacks work without modification
✅ Drop-in replacement for caddy-docker-proxy
✅ All existing deployments migrate successfully
✅ Performance equivalent or better
✅ Comprehensive test coverage (>80%)

---

**Version**: 1.0
**Created**: 2025-11-16
**Target Completion**: 4 weeks
**Status**: Planning Phase
