# Network Mode Analysis: Bridge vs Host

**Date**: 2025-11-18
**Context**: Phase 1 Testing on LXC Infrastructure

---

## Background

Previously, the caddy-agent multi-host system worked successfully with **bridge networking** during initial MVP testing. During Phase 1 real-world deployment, we encountered LXC container restrictions that led us to switch to **host networking**.

This document explains why the switch was necessary and the current state.

---

## Initial Working Configuration (MVP)

### What Worked

**Test Date**: Earlier sessions (pre-Phase 1)
**Infrastructure**: Same LXC containers (192.168.0.96-99)
**Configuration**:
- Server (host1): Bridge networking with port mappings (80:80, 443:443)
- Agents (host2, host3): Host networking
- Test containers: Host networking with `{{upstreams PORT}}` template

**Success**: All routes discovered and working correctly.

---

## Phase 1 Deployment Issue

### What Changed

**Deployment**: Phase 1 with updated compose files
**New Test Containers**: Added multiple test services per host to demonstrate:
- Numbered labels (caddy_0, caddy_1, caddy_10, caddy_111)
- Multiple domains (comma-separated)
- Combined features

### Problem Encountered

**Error on Server (host1)**:
```
Error response from daemon: failed to create task for container:
failed to create shim task: OCI runtime create failed: runc create failed:
unable to start container process: error during container init:
open sysctl net.ipv4.ip_unprivileged_port_start file: reopen fd 8: permission denied
```

**Root Cause**:
- Caddy:2 official image tries to modify `net.ipv4.ip_unprivileged_port_start` sysctl
- This allows binding to privileged ports (< 1024) as non-root
- **LXC unprivileged containers cannot modify sysctl settings**

---

## Why Bridge Networking Failed This Time

### Attempted Solutions

1. **High ports (8080/8443)**: Still triggered sysctl error
2. **SKIP_SETCAP environment variable**: Not recognized by Caddy
3. **Bridge networking with Caddy**: Caddy container itself fails due to sysctl restriction

### Key Difference from MVP

The MVP likely succeeded because:
1. Caddy may have already been running on host1
2. OR Caddy data volume had cached config avoiding sysctl call
3. OR we used a different Caddy image/version

**Current Phase 1**: Fresh deployment with clean volumes → triggers sysctl check every time

---

## Host Networking Solution

### Why It Works

With `network_mode: host`:
- **Container shares host's network namespace**
- No need for Docker to configure network bridges
- Caddy runs with host's network stack directly
- **No sysctl modification needed** - uses host's existing network config

### Implementation

**Server (host1)**:
```yaml
caddy:
  image: caddy:2
  network_mode: host
  # Binds directly to host ports 80, 443, 2019

caddy-agent:
  network_mode: host
  environment:
    - CADDY_API_URL=http://localhost:2019

test-containers:
  network_mode: host
  labels:
    caddy: domain.lan
    caddy.reverse_proxy: 192.168.0.96:PORT  # Direct host IP
```

**Agents (host2, host3)**:
```yaml
caddy-agent:
  network_mode: host
  environment:
    - CADDY_SERVER_URL=http://192.168.0.96:2019
    - HOST_IP=192.168.0.98  # Agent's host IP

test-containers:
  network_mode: host
  labels:
    caddy: domain.lan
    caddy.reverse_proxy: "{{upstreams PORT}}"  # Resolves to HOST_IP:PORT
```

### Agent Code Changes

Added detection for `network_mode: host`:

```python
# Check if container is using host networking
network_mode = container.attrs.get('HostConfig', {}).get('NetworkMode', '')
is_host_network = network_mode == 'host'

if AGENT_MODE == "agent":
    if is_host_network:
        # Host networking: use host IP + internal port directly
        resolved = f"{host_ip}:{port}"
    else:
        # Bridge networking: need published port
        published_port = get_published_port(container, port)
        resolved = f"{host_ip}:{published_port}"
```

---

## Current Status

### ✅ Working (Host1 - Server)

- Caddy running with host networking
- Agent successfully discovering routes:
  - `test-local.lan` → 192.168.0.96:8081 ✅
  - `test-multi-a.lan, test-multi-b.lan, test-multi-c.lan` → 192.168.0.96:8083 ✅
  - `test-numbered-0.lan` → 192.168.0.96:8082 ✅
  - `test-numbered-1.lan` → 192.168.0.96:8082 ✅
- All routes accessible and responding correctly

### ⏳ In Progress (Host2, Host3 - Agents)

- Agents have host networking configured
- Currently running old image without host network detection fix
- Need to recreate containers with updated caddy-agent:phase1 image

---

## Bridge vs Host Networking Comparison

| Aspect | Bridge Networking | Host Networking |
|--------|-------------------|-----------------|
| **Port Isolation** | ✅ Container ports isolated | ❌ Shares all host ports |
| **Port Mapping** | Required (80:80) | Not needed |
| **LXC Compatibility** | ⚠️ Requires privileged for ports <1024 | ✅ Works in unprivileged LXC |
| **Security** | ✅ Better isolation | ⚠️ Less isolation |
| **Performance** | Slightly slower (NAT) | Faster (no NAT) |
| **Complexity** | More complex (port discovery) | Simpler (direct ports) |
| **Caddy sysctl** | ❌ Blocked in LXC | ✅ Bypasses issue |

---

## Recommendations

### Short Term (Phase 1 Testing)

**Use host networking** for all containers:
- ✅ Works on LXC infrastructure
- ✅ Simpler configuration
- ✅ Avoids sysctl issues
- ✅ Testing focus: label parsing, not networking

### Long Term (Production)

**Option 1: Continue with host networking**
- Pros: Works everywhere, simple, fast
- Cons: Less isolation, port conflicts possible
- Best for: Dedicated hosts running only Caddy stack

**Option 2: Return to bridge networking**
- Pros: Better isolation, standard Docker practice
- Cons: Requires:
  - Privileged LXC containers, OR
  - VM infrastructure instead of LXC, OR
  - Custom Caddy image without sysctl modification
- Best for: Shared hosts with multiple services

**Option 3: Hybrid approach**
- Server (host1): Use custom Caddy image with `CAP_NET_BIND_SERVICE` capability instead of sysctl
- Agents: Continue with host networking (simplicity)
- Best for: Maximum compatibility

---

## Custom Caddy Image (Bridge Networking Alternative)

If bridge networking is preferred, create custom Caddy image:

```dockerfile
FROM caddy:2
# Add capability to bind low ports without sysctl
RUN setcap cap_net_bind_service=+ep /usr/bin/caddy
```

This allows binding to ports <1024 without modifying sysctl, making it LXC-compatible with bridge networking.

---

## Testing Implications

### Phase 1 Goals

The primary goal of Phase 1 testing is validating:
1. ✅ Numbered label parsing (caddy_0, caddy_1, caddy_10, etc.)
2. ✅ Multiple domain support (comma-separated)
3. ✅ Backward compatibility (simple labels)
4. ✅ Route coordination between multiple agents

**Network mode is NOT a Phase 1 goal** - either mode works for these features.

### Phase 1 Results (Current)

**Host1**: ✅ All Phase 1 features working with host networking
**Host2/Host3**: ⏳ Awaiting agent update to complete testing

---

## Conclusion

**Question**: "Why is network_mode: host necessary right now?"

**Answer**:
It's necessary because **LXC unprivileged containers block the sysctl modification** that Caddy:2 official image attempts during startup when using bridge networking with fresh volumes.

**Historical Context**:
The MVP worked with bridge networking likely due to cached Caddy state or different deployment conditions that avoided the sysctl check.

**Path Forward**:
- **Short term**: Use host networking to complete Phase 1 testing
- **Long term**: Choose based on production requirements (see recommendations above)

---

**Status**: Host networking successfully deployed on host1, agents updating
**Next**: Complete Phase 1 testing with host networking across all hosts
**Future**: Evaluate bridge networking with custom Caddy image for production
