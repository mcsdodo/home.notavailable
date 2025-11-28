# Quick Start Guide

Get Caddy Agent running in 5 minutes.

## Prerequisites

- Linux host(s) with Docker installed
- SSH access to hosts

## Docker Image

The agent is available as a public Docker image:

```bash
docker pull mcsdodo/caddy-agent:latest
```

No build required - just pull and run!

### Building from Source (Optional)

```bash
git clone <repo>
cd caddy-agent
docker build -t caddy-agent:latest .
```

## Single Host (Easiest)

### 1. Deploy

```bash
docker compose up -d
```

### 3. Add Routes

```bash
docker run -d \
  --name myapp \
  --network host \
  --label caddy=example.com \
  --label caddy.reverse_proxy=localhost:3000 \
  myapp:latest
```

### 4. Test

```bash
curl -H "Host: example.com" http://localhost
```

Done! 🎉

---

## Three Hosts (Production)

### 1. Deploy Host1 (Server)

```bash
scp docker-compose-prod-server.yml root@host1:/opt/caddy/docker-compose.yml

ssh root@host1 << 'EOF'
cd /opt/caddy
docker compose up -d
EOF
```

### 2. Deploy Host2 (Agent)

```bash
scp docker-compose-prod-agent2.yml root@host2:/opt/caddy/docker-compose.yml

ssh root@host2 << 'EOF'
cd /opt/caddy
# Edit docker-compose.yml: change CADDY_URL and HOST_IP to your IPs
docker compose up -d
EOF
```

### 3. Deploy Host3 (Agent)

Same as Host2, but use `docker-compose-prod-agent3.yml`

### 4. Verify

```bash
ssh root@host1 "curl http://localhost:2019/config/apps/http/servers/srv1/routes | jq 'length'"
# Should show routes from caddy-docker-proxy
```

### 5. Add Routes

```bash
# On host2
docker run -d --name app2 --network host \
  --label caddy=app2.example.com \
  --label caddy.reverse_proxy=192.168.1.11:3000 \
  myapp:latest

# On host3
docker run -d --name app3 --network host \
  --label caddy=app3.example.com \
  --label caddy.reverse_proxy=192.168.1.12:3000 \
  myapp:latest

# Wait 5 seconds for agent sync
sleep 5

# Verify routes
ssh root@host1 "curl http://localhost:2019/config/apps/http/servers/srv1/routes | jq 'length'"
# Should show routes from all hosts
```

### 6. Test from Host1

```bash
ssh root@host1 << 'EOF'
curl -H "Host: app2.example.com" http://localhost
curl -H "Host: app3.example.com" http://localhost
EOF
```

---

## Common Commands

### View Routes

```bash
# HTTPS routes (srv1)
curl http://localhost:2019/config/apps/http/servers/srv1/routes | jq '.[] | {id: .["@id"], domain: .match[0].host[0]}'

# HTTP-only routes (srv2)
curl http://localhost:2019/config/apps/http/servers/srv2/routes | jq '.[] | {id: .["@id"], domain: .match[0].host[0]}'
```

### View Logs

```bash
# Agent logs
docker logs caddy-agent-server -f

# Caddy logs
docker logs caddy-server -f

# Combined
docker compose logs -f
```

### Add Container

```bash
docker run -d --name myapp --network host \
  --label caddy=myapp.example.com \
  --label caddy.reverse_proxy=localhost:8080 \
  myimage:tag
```

### Remove Container

```bash
docker rm -f myapp
# Route will disappear within 5 seconds
```

### Check Health

```bash
# Agent running?
docker ps | grep caddy-agent

# Caddy running?
docker ps | grep caddy-server

# API accessible?
curl http://localhost:2019/config/ > /dev/null && echo "OK" || echo "FAIL"

# Routes present?
curl http://localhost:2019/config/apps/http/servers/srv1/routes | jq 'length'
```

### Restart Services

```bash
# Just agent
docker restart caddy-agent-server

# Just caddy
docker restart caddy-server

# Both
docker compose restart
```

---

## Docker Compose Files

All necessary files are in the repo:

- `docker-compose-prod-server.yml` - Server with caddy-docker-proxy (host1)
- `docker-compose-prod-agent2.yml` - Agent (host2)
- `docker-compose-prod-agent3.yml` - Agent (host3)

Just copy and configure with your IPs. Configuration is done via Docker labels.

---

## Documentation

- **DEPLOYMENT.md** - Detailed deployment guide
- **CONFIGURATION.md** - All config options (including HTTP-only routes)
- **TROUBLESHOOTING.md** - Common issues & fixes

---

## Next Steps

1. Add more hosts by copying and modifying the agent compose file
2. Configure your apps with caddy labels
3. Set up DNS pointing to host1
4. For HTTP-only routes, use `http://` prefix: `caddy=http://internal.lan`
5. Monitor with `docker stats` or Prometheus

---

**Version**: 1.1 | **Last Updated**: 2025-11-28

**Need Help?** Check TROUBLESHOOTING.md or create a GitHub issue.

