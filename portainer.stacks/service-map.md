# Service Map: Stacks → Hosts

Generated: 2025-12-13 (Komodo Migration)

---

## How to Update This Service Map

### Source of Truth

With Komodo, the **source of truth** for stack definitions is:
- `portainer.stacks/komodo.toml` - All stack definitions, dependencies, and server assignments

The dependency tree and stack-to-host mapping should match `komodo.toml`. Container inventory can be verified via Komodo UI or CLI.

### Verify Running Containers

To check actual running containers on each LXC:

```bash
# Get all containers with their stack (compose project) assignments
ssh root@<IP> "docker ps --format '{{.Names}}' | xargs -I {} docker inspect {} --format '{{.Name}} -> {{index .Config.Labels \"com.docker.compose.project\"}}'"

# Or for a table view with status:
ssh root@<IP> "docker ps -a --format 'table {{.Names}}\t{{.Status}}'"
```

### Quick check all LXCs (run in parallel):
```bash
ssh root@192.168.0.112 "docker ps --format '{{.Names}}' | xargs -I {} docker inspect {} --format '{{.Name}} -> {{index .Config.Labels \"com.docker.compose.project\"}}'"  # infra
ssh root@192.168.0.212 "docker ps --format '{{.Names}}' | xargs -I {} docker inspect {} --format '{{.Name}} -> {{index .Config.Labels \"com.docker.compose.project\"}}'"  # media-gpu
ssh root@192.168.0.115 "docker ps --format '{{.Names}}' | xargs -I {} docker inspect {} --format '{{.Name}} -> {{index .Config.Labels \"com.docker.compose.project\"}}'"  # frigate-gpu
ssh root@192.168.0.235 "docker ps --format '{{.Names}}' | xargs -I {} docker inspect {} --format '{{.Name}} -> {{index .Config.Labels \"com.docker.compose.project\"}}'"  # frigate
ssh root@192.168.0.238 "docker ps --format '{{.Names}}' | xargs -I {} docker inspect {} --format '{{.Name}} -> {{index .Config.Labels \"com.docker.compose.project\"}}'"  # omada
```

**Note**: The `com.docker.compose.project` label shows the Komodo stack name (e.g., `caddy-infra`, `docker-host-infra-media-gpu`).

---

## Host Overview

| Host | LXC | IP | Purpose |
|------|-----|-----|---------|
| small-main | LXC1 (infra) | 192.168.0.112 | Caddy, observability, networking, Komodo Core |
| big-gpu | LXC2 (media-gpu) | 192.168.0.212 | Media server, GPU workloads |
| big-gpu | LXC3 (frigate-gpu) | 192.168.0.115 | Frigate with GPU |
| small-frigate | LXC4 (frigate) | 192.168.0.235 | Frigate production (Coral) |
| small-frigate | LXC5 (omada) | 192.168.0.238 | Omada controller |

---

## Komodo Stack Dependency Tree

Stacks are deployed in dependency order. Arrows show "depends on" relationships.
Cross-server dependencies are marked with `[server]`.

### LXC1 - Infra (192.168.0.112)
```
observability (foundation for docker-host-infra on all hosts)
    ├── docker-host-infra-infra
    ├── docker-host-infra-media-gpu [media-gpu]
    ├── docker-host-infra-frigate-gpu [frigate-gpu]
    ├── docker-host-infra-frigate [frigate]
    └── docker-host-infra-omada [omada]

caddy-infra (foundation for caddy-agents on all hosts)
    ├── cloudflare
    ├── caddy-media-gpu [media-gpu]
    │       └── cloudflare-agent [media-gpu]
    ├── caddy-frigate-gpu [frigate-gpu]
    ├── caddy-frigate [frigate]
    └── caddy-omada [omada]

infrastructure (independent)
chatgpt (independent)
komodo (independent, runs Core + Periphery)
```

### LXC2 - Media-GPU (192.168.0.212)
```
docker-host-infra-media-gpu (after observability [infra])

caddy-media-gpu (after caddy-infra [infra])
    └── cloudflare-agent

arr (independent)
    └── watchstate

arr-gluetun (independent)
plex (independent)
jellyfin (independent)
emby (independent)
immich (independent)
audiobookshelf (independent)
komga (independent)
paperless (independent)
nut (independent)
stirling-pdf (independent)
komodo (periphery only)
```

### LXC3 - Frigate-GPU (192.168.0.115)
```
docker-host-infra-frigate-gpu (after observability [infra])
caddy-frigate-gpu (after caddy-infra [infra])
surveillance-testing (independent)
komodo (periphery only)
```

### LXC4 - Frigate (192.168.0.235)
```
docker-host-infra-frigate (after observability [infra])
caddy-frigate (after caddy-infra [infra])
surveillance (independent)
komodo (periphery only)
```

### LXC5 - Omada (192.168.0.238)
```
docker-host-infra-omada (after observability [infra])
caddy-omada (after caddy-infra [infra])
omada (independent)
komodo (periphery only)
```

---

## Stack to Host Mapping

| Stack | LXC1 (infra) | LXC2 (media-gpu) | LXC3 (frigate-gpu) | LXC4 (frigate) | LXC5 (omada) |
|-------|:------------:|:----------------:|:------------------:|:--------------:|:------------:|
| arr | | ✅ | | | |
| arr-gluetun | | ✅ | | | |
| audiobookshelf | | ✅ | | | |
| caddy-infra | ✅ | | | | |
| caddy-media-gpu | | ✅ | | | |
| caddy-frigate-gpu | | | ✅ | | |
| caddy-frigate | | | | ✅ | |
| caddy-omada | | | | | ✅ |
| chatgpt | ✅ | | | | |
| cloudflare | ✅ | | | | |
| cloudflare-agent | | ✅ | | | |
| docker-host-infra-infra | ✅ | | | | |
| docker-host-infra-media-gpu | | ✅ | | | |
| docker-host-infra-frigate-gpu | | | ✅ | | |
| docker-host-infra-frigate | | | | ✅ | |
| docker-host-infra-omada | | | | | ✅ |
| emby | | ✅ | | | |
| immich | | ✅ | | | |
| infrastructure | ✅ | | | | |
| jellyfin | | ✅ | | | |
| komga | | ✅ | | | |
| komodo | ✅ (core) | ✅ (periphery) | ✅ (periphery) | ✅ (periphery) | ✅ (periphery) |
| nut | | ✅ | | | |
| observability | ✅ | | | | |
| omada | | | | | ✅ |
| paperless | | ✅ | | | |
| plex | | ✅ | | | |
| stirling-pdf | | ✅ | | | |
| surveillance | | | | ✅ | |
| surveillance-testing | | | ✅ | | |
| watchstate | | ✅ | | | |

---

## Shared Infrastructure

### docker-host-infra (per-host instances)

These containers run on **all hosts** via host-specific stack names:

| Container | LXC1 (infra) | LXC2 (media-gpu) | LXC3 (frigate-gpu) | LXC4 (frigate) | LXC5 (omada) |
|-----------|:------------:|:----------------:|:------------------:|:--------------:|:------------:|
| alloy | ✅ | ✅ | ✅ | ✅ | ✅ |
| watchtower | ✅ | ✅ | ✅ | ✅ | ✅ |
| autoheal | ✅ | ✅ | ✅ | ✅ | ✅ |

### Komodo Distribution

| Component | LXC1 (infra) | LXC2 (media-gpu) | LXC3 (frigate-gpu) | LXC4 (frigate) | LXC5 (omada) |
|-----------|:------------:|:----------------:|:------------------:|:--------------:|:------------:|
| komodo-core | ✅ | | | | |
| komodo-mongo | ✅ | | | | |
| komodo-periphery | ✅ | ✅ | ✅ | ✅ | ✅ |

### Caddy Distribution

`caddy-agent` is deployed via host-specific caddy stacks:

| Host | Stack Name |
|------|------------|
| LXC1 (infra) | caddy-infra |
| LXC2 (media-gpu) | caddy-media-gpu |
| LXC3 (frigate-gpu) | caddy-frigate-gpu |
| LXC4 (frigate) | caddy-frigate |
| LXC5 (omada) | caddy-omada |

