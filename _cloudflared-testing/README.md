# Caddy Testing Environment with DockFlare

This project demonstrates automatic reverse proxy configuration using Caddy and Cloudflare Tunnel integration with DockFlare.

## Components

- **DockFlare**: Automatically creates and manages Cloudflare Tunnels for Docker containers
- **Redis**: Backend for DockFlare state management
- **Sample Services**: webserver and webserver2 (http-echo), my-service (nginx)

## Features

### DockFlare Integration
- Automatically creates Cloudflare Tunnels for labeled containers
- Manages DNS records and SSL certificates via Cloudflare
- Provides secure access to local services through Cloudflare's edge network

## Setup Process

### 1. Prerequisites
- Docker Desktop on Windows
- Cloudflare account with:
  - API Token with proper permissions
  - Account ID
  - Zone ID

### 2. Configuration

Create a `.env` file in the directory:
```env
CF_API_TOKEN=your_cloudflare_api_token
CF_ACCOUNT_ID=your_cloudflare_account_id
CF_ZONE_ID=your_cloudflare_zone_id
```

### 4. Container Labels

#### For DockFlare (Cloudflare Tunnel)
```yaml
labels:
  dockflare.enable: true
  dockflare.hostname: example.yourdomain.com
  dockflare.service: http://container-name:80
```

## Troubleshooting

### Issue 1: Docker Daemon Connection Refused

**Problem**: DockFlare cannot connect to Docker daemon.

**Error**:
```
Failed to connect to Docker daemon: Error while fetching server API version: 
('Connection aborted.', PermissionError(13, 'Permission denied'))
```

**Solution**: On Windows, the Docker socket path needs to be prefixed with `//`:
```yaml
volumes:
  - //var/run/docker.sock:/var/run/docker.sock:ro
```

Also ensure the container runs with proper permissions:
```yaml
user: "0:0"  # Run as root
```

### Issue 3: Cloudflare API Authentication Errors

**Problem**: DockFlare fails with 403 Forbidden errors.

**Error**:
```
Authentication error (code 10000)
Valid user-level authentication not found (code 9109)
```

**Solution**: Ensure your Cloudflare API token has the following permissions:
- **Account** → **Cloudflare Access** → **Edit**
- **Account** → **Access: Service Tokens** → **Edit**
- **Zone** → **DNS** → **Edit**
- **User** → **Read**

Create a new token at: Cloudflare Dashboard → My Profile → API Tokens

### Issue 4: Cloudflare Tunnel Cannot Reach Services

**Problem**: DockFlare tunnel shows "no such host" errors.

**Error**:
```json
{
  "error": "Unable to reach the origin service. The service may be down or it may not be responding to traffic from cloudflared: dial tcp: lookup my-service on 127.0.0.11:53: no such host",
  "originService": "http://my-service:80"
}
```

**Root Cause**: The cloudflared agent container is not on the same Docker network as the target services.

**Solution**:

1. Ensure target services are on the `dockflare-internal` network:
```yaml
my-service:
  image: nginx:latest
  networks:
    - dockflare-internal
  labels:
    - "dockflare.enable=true"
    - "dockflare.hostname=my-service.yourdomain.com"
    - "dockflare.service=http://my-service:80"
```

2. Connect the cloudflared agent to the network:
```bash
docker network connect dockflare-internal cloudflared-agent-dockflare-tunnel
docker restart cloudflared-agent-dockflare-tunnel
```

3. Verify connectivity from within dockflare container:
```bash
docker exec dockflare wget -O- http://my-service:80
```

### Issue 5: Cloudflare API Rate Limiting

**Problem**: Too many API requests cause rate limiting.

**Error**:
```
429 Client Error: Too Many Requests
Rate limited. Please wait and consider throttling your request speed (code 10429)
```

**Solution**: Wait 5-10 minutes for the rate limit to reset. Avoid repeatedly restarting the DockFlare container during troubleshooting.

### Issue 6: AttributeError on proxy_target.strip()

**Problem**: Python script crashes when processing containers without labels.

**Error**:
```
AttributeError: 'NoneType' object has no attribute 'strip'
```

**Solution**: Check if proxy_target is not None before calling strip():
```python
upstreams_match = re.match(r"\{\{upstreams (\d+)}}", proxy_target.strip()) if proxy_target else None
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Networks                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────┐     │
│  │         dockflare-internal Network               │     │
│  │                                                   │     │
│  │  ┌─────────────┐  ┌──────────────┐              │     │
│  │  │  DockFlare  │  │    Redis     │              │     │
│  │  └─────────────┘  └──────────────┘              │     │
│  │         │                                        │     │
│  │  ┌──────┴────────────────────────┐              │     │
│  │  │  webserver2    my-service     │              │     │
│  │  └───────────────────────────────┘              │     │
│  │         ▲                                        │     │
│  │         │                                        │     │
│  │  ┌──────┴─────────────────────────────────┐    │     │
│  │  │  cloudflared-agent-dockflare-tunnel    │    │     │
│  │  └────────────────────────────────────────┘    │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
│  ┌──────────────────────────────────────────────────┐     │
│  │         Default Bridge Network                   │     │
│  │                                                   │     │
│  │  ┌─────────────┐  ┌──────────────┐              │     │
│  │  │    Caddy    │  │ Caddy Agent  │              │     │
│  │  └─────────────┘  └──────────────┘              │     │
│  │         ▲                ▲                       │     │
│  │         │                │                       │     │
│  │     API:2019     Docker Socket                   │     │
│  └──────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
              Cloudflare Edge Network
```

## Usage

### Start Services
```bash
docker compose -f caddy-testing/docker-compose.yml up -d
```

### Check Logs
```bash
# Caddy agent logs
docker logs caddy-agent --tail 50

# DockFlare logs
docker logs dockflare --tail 50

# Cloudflared tunnel logs
docker logs cloudflared-agent-dockflare-tunnel --tail 50
```

### Test Local Access
```bash
# Via Caddy (if configured)
curl http://localhost/

# Direct to service
curl http://webserver2:80
```

### Test Cloudflare Tunnel Access
```bash
curl https://my-service.yourdomain.com/
curl https://test.yourdomain.com/
```

### Verify Network Connectivity
```bash
# From DockFlare container
docker exec dockflare wget -O- http://my-service:80

# From cloudflared container (requires reconnecting to network)
docker network connect dockflare-internal cloudflared-agent-dockflare-tunnel
docker restart cloudflared-agent-dockflare-tunnel
```

## Configuration Files

### Generated Files
- `caddy-output.json`: Local copy of Caddy configuration maintained by the agent
- `dockflare_data/`: Persistent storage for DockFlare state
- `dockflare_redis/`: Redis data

### Environment Variables

#### Caddy Agent
- `CADDY_API_URL`: Caddy admin API endpoint (default: `http://caddy:2019`)
- `DOCKER_LABEL_PREFIX`: Label prefix to watch (default: `caddy`)

#### DockFlare
- `CF_API_TOKEN`: Cloudflare API token
- `CF_ACCOUNT_ID`: Cloudflare account ID
- `CF_ZONE_ID`: Cloudflare zone ID
- `REDIS_URL`: Redis connection URL
- `DOCKER_HOST`: Docker socket path
- `LOG_LEVEL`: Logging level (ERROR, INFO, DEBUG)

## Best Practices

1. **Security**: Use read-only Docker socket mounts when possible (`:ro`)
2. **Networking**: Keep services on dedicated networks for isolation
3. **Monitoring**: Regularly check logs for errors and rate limiting
4. **Configuration**: Maintain local backups of generated configurations
5. **Rate Limits**: Avoid excessive container restarts to prevent API throttling

## References

- [Caddy Documentation](https://caddyserver.com/docs/)
- [DockFlare GitHub](https://github.com/ChrispyBacon-dev/DockFlare)
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
