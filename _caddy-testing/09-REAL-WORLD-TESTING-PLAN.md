# Real-World Testing Plan

Deployment and testing plan for caddy-agent Phase 1 on actual infrastructure.

## Current Infrastructure

### Test Hosts (192.168.0.96-99)
| Host | IP | Role | Current Setup |
|------|------|------|---------------|
| host1 | 192.168.0.96 | Server | Caddy + Agent (server mode) + test-local |
| host2 | 192.168.0.98 | Agent | Agent (agent mode) + test-remote |
| host3 | 192.168.0.99 | Agent | Agent (agent mode) + test-host3 |

**Status**: Running with Phase 1 features (bridge networking)

### Production Hosts (192.168.0.20-23)
| Host | IP | Services | Current Caddy |
|------|------|----------|---------------|
| host 20 | 192.168.0.20 | ? | caddy-docker-proxy chain start |
| host 21 | 192.168.0.21 | small stack | caddy-docker-proxy |
| host 22 | 192.168.0.22 | big-media stack | caddy-docker-proxy |
| host 23 | 192.168.0.23 | ? | caddy-docker-proxy chain end |

**Status**: Running lucaslorentz/caddy-docker-proxy
**Risk**: Production - needs careful migration

---

## Phase 1: Test Environment Validation (This Week)

### Objective
Validate Phase 1 features on test hosts (96-99) with production-like workloads.

### Test Plan

#### Test 1.1: Deploy Real Services to Test Hosts

**Goal**: Run actual services from portainer.stacks on test environment

**Deploy to host2 (192.168.0.98)**:
```yaml
# Simple service - jellyfin-like
services:
  test-simple:
    image: hashicorp/http-echo
    container_name: test-jellyfin
    networks:
      - caddy
    labels:
      caddy: http://jellyfin-test.lan
      caddy.reverse_proxy: "{{upstreams 8096}}"
    command: ["-listen=:8096", "-text=Jellyfin Test"]

# Multi-domain service - sonarr-like
  test-multi:
    image: hashicorp/http-echo
    container_name: test-sonarr
    networks:
      - caddy
    labels:
      caddy_0: http://series-test.lan, http://sonarr-test.lan
      caddy_0.reverse_proxy: "{{upstreams 8989}}"
    command: ["-listen=:8989", "-text=Sonarr Test"]

# Numbered labels - caddy-config-like
  test-numbered:
    image: hashicorp/http-echo
    container_name: test-config
    networks:
      - caddy
    labels:
      caddy_10: http://route10-test.lan
      caddy_10.reverse_proxy: "{{upstreams 10000}}"
      caddy_111: http://route111-test.lan
      caddy_111.reverse_proxy: "{{upstreams 11100}}"
    command: ["-listen=:10000", "-text=Route 10"]
```

**Expected Results**:
- ✅ Simple service: 1 route
- ✅ Multi-domain: 1 route with 2 domains
- ✅ Numbered: 2 routes from same container

**Pass Criteria**:
- All routes discovered within 5 seconds
- All domains respond correctly
- External access works (curl from Windows host)

---

#### Test 1.2: Stress Test with Multiple Containers

**Goal**: Simulate production load with many containers

**Deploy to host3 (192.168.0.99)**:
```bash
# Create 10 containers with different label patterns
for i in {1..10}; do
  docker run -d \
    --name stress-test-$i \
    --network caddy \
    --label caddy="stress-$i.lan" \
    --label caddy.reverse_proxy="stress-test-$i:$((8000+i))" \
    hashicorp/http-echo \
    -listen=:$((8000+i)) \
    -text="Stress test $i"
done
```

**Expected Results**:
- ✅ All 10 routes discovered
- ✅ No route conflicts
- ✅ Agent performance acceptable (< 100ms per sync)

**Pass Criteria**:
- Agent CPU usage < 10%
- Memory usage < 100MB
- All routes accessible

---

#### Test 1.3: Dynamic Updates

**Goal**: Test container lifecycle management

**Test Scenario**:
```bash
# 1. Add container
docker run -d --name dynamic-1 --network caddy \
  --label caddy=dynamic-1.lan \
  --label caddy.reverse_proxy="dynamic-1:9000" \
  hashicorp/http-echo -listen=:9000 -text="Dynamic 1"

# Wait and verify
sleep 5
curl -H "Host: dynamic-1.lan" http://192.168.0.96

# 2. Remove container
docker rm -f dynamic-1
sleep 5
# Verify route removed

# 3. Restart container with different labels
docker run -d --name dynamic-1 --network caddy \
  --label caddy_0="dynamic-new-a.lan" \
  --label caddy_0.reverse_proxy="dynamic-1:9000" \
  --label caddy_1="dynamic-new-b.lan" \
  --label caddy_1.reverse_proxy="dynamic-1:9001" \
  hashicorp/http-echo -listen=:9000 -text="Dynamic Updated"

# Verify 2 new routes created
```

**Pass Criteria**:
- Route added within 5 seconds
- Route removed within 5 seconds
- Updated routes reflect new labels
- No stale routes remain

---

## Phase 2: Staging Deployment (Next Week)

### Objective
Deploy Phase 1 agent alongside existing caddy-docker-proxy for A/B testing.

### Architecture

```
┌─────────────────────────────────────────┐
│  host 21 (192.168.0.21)                 │
│  ┌────────────────────┐                 │
│  │ caddy-docker-proxy │ (Port 80/443)   │
│  │ (existing)         │                 │
│  └────────────────────┘                 │
│                                          │
│  ┌────────────────────┐                 │
│  │ caddy-agent        │ (Watch only)    │
│  │ (Phase 1)          │                 │
│  └────────────────────┘                 │
│         │                                │
│         └─ Log routes (compare)         │
└──────────────────────────────────────────┘
```

### Deployment Steps

#### Step 1: Deploy Agent in Watch-Only Mode

**New Environment Variable**: `AGENT_DRY_RUN=true`

```yaml
# On host 21 - alongside existing caddy-docker-proxy
services:
  caddy-agent-watch:
    image: caddy-agent:phase1
    container_name: caddy-agent-staging
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - AGENT_MODE=standalone
      - AGENT_ID=host21-staging
      - CADDY_API_URL=http://localhost:3019  # Different port
      - AGENT_DRY_RUN=true  # Don't push to Caddy, just log
    networks:
      - caddy
```

**What This Does**:
- Watches all containers on caddy network
- Generates routes (Phase 1 logic)
- Logs what it would do
- **Doesn't actually update Caddy**

#### Step 2: Compare Routes

**Script**: `compare-routes.sh`
```bash
#!/bin/bash

# Get routes from caddy-docker-proxy
echo "=== caddy-docker-proxy routes ==="
curl -s http://192.168.0.21:2019/config/apps/http/servers | \
  jq '.[] | .routes[] | .["@id"]' | sort

# Get routes from caddy-agent (dry-run logs)
echo "=== caddy-agent would create ==="
docker logs caddy-agent-staging 2>&1 | \
  grep "Route:" | awk '{print $NF}' | sort

# Compare
echo "=== Differences ==="
diff <(curl -s http://192.168.0.21:2019/config/apps/http/servers | jq '.[] | .routes[] | .["@id"]' | sort) \
     <(docker logs caddy-agent-staging 2>&1 | grep "Route:" | awk '{print $NF}' | sort)
```

**Expected Result**: **IDENTICAL** (Phase 1 features only)

**If Differences Found**:
- Analyze missing/extra routes
- Identify Phase 2/3 features needed
- Document for next phase

---

## Phase 3: Controlled Migration (Week 3)

### Objective
Migrate one production host to caddy-agent while keeping rollback option.

### Target Host: 192.168.0.21 (small stack)

**Why this host**:
- Uses simple labels mostly
- Has numbered labels (caddy_10, caddy_20) - tests Phase 1
- Lower risk than media servers
- Easy to rollback

### Migration Steps

#### Pre-Migration Checklist
- [ ] Backup current docker-compose.yml
- [ ] Document all current routes
- [ ] Test rollback procedure
- [ ] Alert monitoring (if any)

#### Step 1: Deploy Agent Alongside

```yaml
version: '3'
services:
  # Keep existing caddy-docker-proxy on port 80/443
  caddy-old:
    image: lucaslorentz/caddy-docker-proxy:latest
    container_name: caddy-docker-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - CADDY_INGRESS_NETWORKS=caddy
    networks:
      - caddy

  # New caddy-agent on port 8080/8443 (test)
  caddy-new:
    image: caddy:2
    container_name: caddy-new
    ports:
      - "8080:80"
      - "8443:443"
      - "3019:2019"
    networks:
      - caddy

  caddy-agent-new:
    image: caddy-agent:phase1
    container_name: caddy-agent-new
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - AGENT_MODE=standalone
      - AGENT_ID=host21-new
      - CADDY_API_URL=http://caddy-new:2019
    networks:
      - caddy
```

**Test Both**:
```bash
# Old (port 80)
curl -H "Host: app.lacny.me" http://192.168.0.21

# New (port 8080)
curl -H "Host: app.lacny.me" http://192.168.0.21:8080

# Compare responses
```

#### Step 2: Switch Traffic (if tests pass)

**Swap ports**:
```yaml
services:
  caddy-old:
    ports:
      - "8080:80"  # Moved to 8080
      - "8443:443"

  caddy-new:
    ports:
      - "80:80"  # Now on 80
      - "443:443"
```

**Monitor for 24 hours**:
- Check all services accessible
- Monitor error logs
- Check certificate renewal (if any)

#### Step 3: Remove Old (if successful)

After 24-48 hours of stable operation:
```bash
docker stop caddy-old
docker rm caddy-old
# Update compose to remove old service
```

---

## Phase 4: Full Migration (Week 4)

### Remaining Hosts
- host 22 (big-media) - Needs Phase 3 (header_up)
- host 20 & 23 - Chain configuration

### Prerequisites
Before migrating:
- [ ] Phase 1 stable on host 21 for 1+ week
- [ ] Phase 2 implemented (if needed for wildcards)
- [ ] Phase 3 implemented (if needed for headers)

---

## Rollback Procedures

### Scenario 1: Agent Crashes/Fails

**Immediate Rollback** (< 5 minutes):
```bash
# Stop agent
docker stop caddy-agent-new

# Start old caddy-docker-proxy
docker start caddy-old

# Switch ports back
docker-compose -f docker-compose-backup.yml up -d
```

### Scenario 2: Routes Not Working

**Debug First**:
```bash
# Check what agent generated
docker logs caddy-agent-new | grep "Route:"

# Check what Caddy has
curl http://localhost:2019/config/apps/http/servers

# Compare
```

**If Unfixable** - Rollback as above

### Scenario 3: Performance Issues

**Metrics to Monitor**:
- Agent CPU usage (should be < 5% average)
- Agent memory (should be < 100MB)
- Route sync time (should be < 2 seconds)
- Caddy response time (should be identical to old)

**If Degraded** - Investigate before rollback

---

## Success Criteria

### Phase 1 Testing (Test Hosts)
- ✅ All test scenarios pass
- ✅ No route conflicts
- ✅ Performance acceptable
- ✅ Dynamic updates work

### Phase 2 Staging
- ✅ Routes match caddy-docker-proxy exactly
- ✅ No regressions identified
- ✅ All services accessible

### Phase 3 Migration (Host 21)
- ✅ Stable for 1+ week
- ✅ All services working
- ✅ No rollbacks needed
- ✅ Certificates renewing

### Phase 4 Full Migration
- ✅ All hosts migrated
- ✅ caddy-docker-proxy removed
- ✅ Production stable

---

## Timeline

| Week | Phase | Activities | Deliverables |
|------|-------|------------|--------------|
| 1 (Current) | Phase 1 Testing | Run tests on 96-99 hosts | Test results, performance data |
| 2 | Staging | Deploy dry-run on host 21 | Route comparison, gap analysis |
| 3 | Migration | Migrate host 21 | Migrated host, rollback tested |
| 4 | Full Rollout | Migrate remaining hosts | All hosts on caddy-agent |

---

## Files & Scripts

### Deploy Scripts

**`deploy-test-services.sh`** - Deploy test workload
```bash
#!/bin/bash
# Deploy to host2 (98)
scp docker-compose-test.yml root@192.168.0.98:/root/testing/
ssh root@192.168.0.98 "cd /root/testing && docker-compose up -d"
```

**`compare-routes.sh`** - Compare old vs new
```bash
#!/bin/bash
# Compare routes between caddy-docker-proxy and caddy-agent
# (Script content above)
```

**`monitor.sh`** - Monitor agent health
```bash
#!/bin/bash
while true; do
  echo "$(date) - CPU: $(docker stats caddy-agent-new --no-stream --format '{{.CPUPerc}}') - Mem: $(docker stats caddy-agent-new --no-stream --format '{{.MemUsage}}')"
  sleep 60
done
```

### Compose Files

**`docker-compose-test-services.yml`** - Test workload
**`docker-compose-staging.yml`** - Staging on host 21
**`docker-compose-migration.yml`** - Migration config

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Routes not discovered | Low | High | Extensive testing, dry-run mode |
| Performance degradation | Low | Medium | Monitoring, rollback plan |
| Certificate issues | Medium | High | Keep old Caddy data volume |
| DNS/Network issues | Low | High | Test on staging first |
| Agent crashes | Low | High | Restart policy, monitoring |

---

## Communication Plan

### Stakeholders
- You (primary)
- Other users (if any)

### Updates
- Daily during testing
- Before each migration
- Immediate on any issues

---

## Next Action

**Immediate** (This Week):
1. Deploy test services to host2 (98)
2. Run Test 1.1 (Real services)
3. Run Test 1.2 (Stress test)
4. Run Test 1.3 (Dynamic updates)
5. Document results

**Ready to start?** I can:
1. Create the test compose files
2. Deploy to host2 (98)
3. Run all tests
4. Collect results

---

**Version**: 1.0
**Created**: 2025-11-18
**Status**: Ready for Execution
