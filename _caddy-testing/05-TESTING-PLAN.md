# Testing Plan - Caddy Multi-Host Agent System

**Purpose**: Verify multi-host reverse proxy functionality, reliability, and edge cases.

---

## Test Environment

**Hosts**:
- host1 (192.168.0.96) - Server
- host2 (192.168.0.98) - Agent
- host3 (192.168.0.99) - Agent

**Prerequisites**:
```bash
# All hosts
sysctl -w net.ipv4.ip_unprivileged_port_start=80

# Build and save image
cd c:\_dev\home.notavailable\_caddy-testing
docker build -t caddy-agent:latest .
docker save caddy-agent:latest | gzip > caddy-agent.tar.gz
```

---

## 1. Deployment Tests

### 1.1 Fresh Deployment
**Goal**: Verify clean deployment on all hosts.

```bash
# Deploy server
scp caddy-agent.tar.gz docker-compose-prod-server.yml Caddyfile root@192.168.0.96:/root/caddy-multihost/
ssh root@192.168.0.96 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-server.yml up -d"

# Deploy agents
scp caddy-agent.tar.gz docker-compose-prod-agent2.yml root@192.168.0.98:/root/caddy-multihost/
ssh root@192.168.0.98 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-agent2.yml up -d"

scp caddy-agent.tar.gz docker-compose-prod-agent3.yml root@192.168.0.99:/root/caddy-multihost/
ssh root@192.168.0.99 "cd /root/caddy-multihost && gunzip -c caddy-agent.tar.gz | docker load && docker compose -f docker-compose-prod-agent3.yml up -d"
```

**Verify**:
```bash
# Check all containers running
ssh root@192.168.0.96 "docker ps | grep -E '(caddy|test)'"
ssh root@192.168.0.98 "docker ps | grep -E '(caddy|test)'"
ssh root@192.168.0.99 "docker ps | grep -E '(caddy|test)'"

# Expected: 3 containers on host1, 2 on host2/host3
```

**Pass Criteria**: ✅ All containers in "Up" status

### 1.2 Agent Connectivity
**Goal**: Verify agents connect to server.

```bash
# Check agent logs for successful connection
ssh root@192.168.0.96 "docker logs caddy-agent-server 2>&1 | grep -E '(Syncing|updated successfully)'"
ssh root@192.168.0.98 "docker logs caddy-agent-remote 2>&1 | grep -E '(Syncing|updated successfully)'"
ssh root@192.168.0.99 "docker logs caddy-agent-remote3 2>&1 | grep -E '(Syncing|updated successfully)'"
```

**Pass Criteria**: ✅ All agents show "✅ Caddy config updated successfully"

---

## 2. Routing Tests

### 2.1 Basic Route Discovery
**Goal**: Verify all routes are discovered and configured.

```bash
# Check routes in Caddy
ssh root@192.168.0.96 "curl -s http://localhost:2019/config/apps/http/servers/reverse_proxy/routes | jq -r '.[] | .\"@id\"'"
```

**Expected Output**:
```
host1-server_test-local
host2-remote_test-remote
host3-remote_test-host3
```

**Pass Criteria**: ✅ All 3 routes present

### 2.2 HTTP Routing
**Goal**: Verify traffic reaches correct containers.

```bash
# Test each route
ssh root@192.168.0.96 "curl -s -H 'Host: test-local.lan' http://localhost"
# Expected: Hello from host1

ssh root@192.168.0.96 "curl -s -H 'Host: test-remote.lan' http://localhost"
# Expected: Hello from host2

ssh root@192.168.0.96 "curl -s -H 'Host: test-host3.lan' http://localhost"
# Expected: Hello from host3
```

**Pass Criteria**: ✅ Each returns correct "Hello from hostX" message

### 2.3 External Access
**Goal**: Verify routing works from external client.

```bash
# From Windows host
curl -H "Host: test-local.lan" http://192.168.0.96
curl -H "Host: test-remote.lan" http://192.168.0.96
curl -H "Host: test-host3.lan" http://192.168.0.96
```

**Pass Criteria**: ✅ All routes accessible from external network

---

## 3. Dynamic Update Tests

### 3.1 Container Addition
**Goal**: Verify new containers are auto-discovered.

```bash
# Add new container on host2
ssh root@192.168.0.98 "docker run -d --name test-new --network host hashicorp/http-echo -listen=:8888 -text='New container' || true"
ssh root@192.168.0.98 "docker update --label-add caddy=test-new.lan --label-add 'caddy.reverse_proxy=192.168.0.98:8888' test-new"

# Wait for agent update
sleep 5

# Check route added
ssh root@192.168.0.96 "curl -s http://localhost:2019/config/apps/http/servers/reverse_proxy/routes | jq -r '.[] | select(.\"@id\" == \"host2-remote_test-new\")'"

# Test routing
ssh root@192.168.0.96 "curl -s -H 'Host: test-new.lan' http://localhost"
```

**Pass Criteria**: ✅ New route discovered and working

### 3.2 Container Removal
**Goal**: Verify removed containers update routes.

```bash
# Remove container
ssh root@192.168.0.98 "docker rm -f test-new"

# Wait for agent update
sleep 5

# Verify route removed
ssh root@192.168.0.96 "curl -s http://localhost:2019/config/apps/http/servers/reverse_proxy/routes | jq -r '.[] | .\"@id\"' | grep test-new"
# Expected: Empty output
```

**Pass Criteria**: ✅ Route removed from Caddy config

### 3.3 Container Restart
**Goal**: Verify restarted containers maintain routes.

```bash
# Restart container
ssh root@192.168.0.98 "docker restart test-remote"

# Wait for agent update
sleep 5

# Test routing still works
ssh root@192.168.0.96 "curl -s -H 'Host: test-remote.lan' http://localhost"
```

**Pass Criteria**: ✅ Route persists after restart

---

## 4. Multi-Agent Coordination Tests

### 4.1 Concurrent Updates
**Goal**: Verify agents don't overwrite each other's routes.

```bash
# Add containers simultaneously on host2 and host3
ssh root@192.168.0.98 "docker run -d --name concurrent2 --network host --label caddy=concurrent2.lan --label caddy.reverse_proxy=192.168.0.98:7000 hashicorp/http-echo -listen=:7000 -text='Concurrent2'" &
ssh root@192.168.0.99 "docker run -d --name concurrent3 --network host --label caddy=concurrent3.lan --label caddy.reverse_proxy=192.168.0.99:7001 hashicorp/http-echo -listen=:7001 -text='Concurrent3'" &
wait

# Wait for agent updates
sleep 5

# Verify both routes exist
ssh root@192.168.0.96 "curl -s http://localhost:2019/config/apps/http/servers/reverse_proxy/routes | jq -r '.[] | .\"@id\"' | grep -E '(concurrent2|concurrent3)' | wc -l"
# Expected: 2

# Clean up
ssh root@192.168.0.98 "docker rm -f concurrent2"
ssh root@192.168.0.99 "docker rm -f concurrent3"
```

**Pass Criteria**: ✅ Both routes present, no overwrites

### 4.2 Agent Isolation
**Goal**: Verify each agent only updates its own routes.

```bash
# Check route ownership
ssh root@192.168.0.96 "curl -s http://localhost:2019/config/apps/http/servers/reverse_proxy/routes" | jq -r '.[] | {id: ."@id", host: .match[0].host[0]}'
```

**Expected**: Each route prefixed with correct agent ID:
- `host1-server_*` for local containers
- `host2-remote_*` for host2 containers
- `host3-remote_*` for host3 containers

**Pass Criteria**: ✅ No route ID collisions

---

## 5. Failure Scenario Tests

### 5.1 Agent Failure
**Goal**: Verify system handles agent failure gracefully.

```bash
# Stop agent on host2
ssh root@192.168.0.98 "docker stop caddy-agent-remote"

# Verify existing routes still work
ssh root@192.168.0.96 "curl -s -H 'Host: test-remote.lan' http://localhost"
# Expected: Still works

# Verify stale routes remain (known issue)
ssh root@192.168.0.96 "curl -s http://localhost:2019/config/apps/http/servers/reverse_proxy/routes | jq -r '.[] | .\"@id\"' | grep host2-remote"
# Expected: Routes still present

# Restart agent
ssh root@192.168.0.98 "docker start caddy-agent-remote"

# Wait for reconnection
sleep 5
```

**Pass Criteria**: ✅ Routes persist during outage, agent reconnects

### 5.2 Server Restart
**Goal**: Verify agents recover from server restart.

```bash
# Restart Caddy server
ssh root@192.168.0.96 "docker restart caddy-server"

# Wait for startup
sleep 10

# Check agent logs for reconnection
ssh root@192.168.0.98 "docker logs caddy-agent-remote --tail 5 | grep 'updated successfully'"
ssh root@192.168.0.99 "docker logs caddy-agent-remote3 --tail 5 | grep 'updated successfully'"

# Verify routes restored
ssh root@192.168.0.96 "curl -s -H 'Host: test-remote.lan' http://localhost"
```

**Pass Criteria**: ✅ All agents reconnect, routes restored

### 5.3 Network Partition
**Goal**: Verify behavior during network issues.

```bash
# Block port 2019 on host1
ssh root@192.168.0.96 "iptables -A INPUT -p tcp --dport 2019 -s 192.168.0.98 -j DROP"

# Wait for agent update attempt
sleep 10

# Check agent logs for errors
ssh root@192.168.0.98 "docker logs caddy-agent-remote --tail 10"
# Expected: Connection errors

# Restore connectivity
ssh root@192.168.0.96 "iptables -D INPUT -p tcp --dport 2019 -s 192.168.0.98 -j DROP"

# Verify recovery
sleep 5
ssh root@192.168.0.98 "docker logs caddy-agent-remote --tail 5 | grep 'updated successfully'"
```

**Pass Criteria**: ✅ Agent logs errors, recovers when connectivity restored

---

## 6. Performance Tests

### 6.1 Multiple Containers
**Goal**: Verify system handles many containers.

```bash
# Create 10 containers on host2
for i in {1..10}; do
  ssh root@192.168.0.98 "docker run -d --name perf-test-$i --network host --label caddy=perf-$i.lan --label caddy.reverse_proxy=192.168.0.98:$((9000+i)) hashicorp/http-echo -listen=:$((9000+i)) -text='Container $i'"
done

# Wait for discovery
sleep 10

# Verify all routes added
ssh root@192.168.0.96 "curl -s http://localhost:2019/config/apps/http/servers/reverse_proxy/routes | jq -r '.[] | .\"@id\"' | grep 'host2-remote_perf' | wc -l"
# Expected: 10

# Test random route
ssh root@192.168.0.96 "curl -s -H 'Host: perf-5.lan' http://localhost"

# Cleanup
for i in {1..10}; do
  ssh root@192.168.0.98 "docker rm -f perf-test-$i"
done
```

**Pass Criteria**: ✅ All 10 routes discovered and working

### 6.2 Rapid Updates
**Goal**: Verify debouncing handles rapid changes.

```bash
# Rapidly restart container
for i in {1..5}; do
  ssh root@192.168.0.98 "docker restart test-remote"
  sleep 1
done

# Wait for debounce
sleep 5

# Verify route still works
ssh root@192.168.0.96 "curl -s -H 'Host: test-remote.lan' http://localhost"
```

**Pass Criteria**: ✅ Route remains functional after rapid restarts

---

## 7. Edge Cases

### 7.1 Invalid Labels
**Goal**: Verify agent handles malformed labels gracefully.

```bash
# Container with missing reverse_proxy label
ssh root@192.168.0.98 "docker run -d --name invalid-labels --network host --label caddy=invalid.lan hashicorp/http-echo -listen=:9999 -text='Invalid'"

# Wait
sleep 5

# Check agent logs for errors (should handle gracefully)
ssh root@192.168.0.98 "docker logs caddy-agent-remote --tail 20 | grep -i error"

# Cleanup
ssh root@192.168.0.98 "docker rm -f invalid-labels"
```

**Pass Criteria**: ✅ Agent logs issue but continues operating

### 7.2 Port Conflicts
**Goal**: Verify behavior when port already in use.

```bash
# Start container on port 8080 (conflicts with test-remote)
ssh root@192.168.0.98 "docker run -d --name conflict-test --network host --label caddy=conflict.lan --label caddy.reverse_proxy=192.168.0.98:8080 hashicorp/http-echo -listen=:8888 -text='Conflict'" || echo "Expected: Port may already be in use"

# Check if route created
ssh root@192.168.0.96 "curl -s -H 'Host: conflict.lan' http://localhost"

# Cleanup
ssh root@192.168.0.98 "docker rm -f conflict-test"
```

**Pass Criteria**: ✅ System handles conflict without crashing

---

## Test Summary Template

```
# Test Run: [DATE]

## Environment
- Host1: [IP] - [Caddy Version] - [Agent Version]
- Host2: [IP] - [Agent Version]
- Host3: [IP] - [Agent Version]

## Results
[ ] 1. Deployment Tests (1.1, 1.2)
[ ] 2. Routing Tests (2.1, 2.2, 2.3)
[ ] 3. Dynamic Updates (3.1, 3.2, 3.3)
[ ] 4. Multi-Agent (4.1, 4.2)
[ ] 5. Failure Scenarios (5.1, 5.2, 5.3)
[ ] 6. Performance (6.1, 6.2)
[ ] 7. Edge Cases (7.1, 7.2)

## Issues Found
- [List any failures or unexpected behavior]

## Notes
- [Additional observations]
```

---

## Automated Testing Script (TODO)

Create `test-all.sh`:
```bash
#!/bin/bash
# Automated test runner
# Usage: ./test-all.sh

# Run all tests and collect results
# Generate test report
# Exit with code 0 if all pass, 1 if any fail
```

---

**Next Steps**:
1. Run full test suite against current deployment
2. Document any failures in GitHub issues
3. Create automated test script
4. Add continuous testing in CI/CD
