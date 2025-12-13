# Post-Migration Cleanup: Folder Reorganization + ResourceSync Consolidation

## Goal

Reorganize from service-centric flat structure to LXC-based hierarchy, and replace 8 migration-phase syncs with Foundation + Per-LXC syncs.

## Current State

```
portainer.stacks/
├── arr/
├── arr-gluetun/
├── audiobookshelf/
├── caddy/
├── chatgpt/
├── cloudflare/
├── cloudflare-agent/
├── docker-host-infra/
├── emby/
├── immich/
├── infrastructure/
├── jellyfin/
├── komga/
├── komodo/
├── nut/
├── observability/
├── omada/
├── paperless/
├── plex/
├── stirling-pdf/
├── surveillance/
│   ├── frigate/
│   └── frigate-gpu/
└── watchstate/
```

**Problems:**
- Unclear which stacks run on which server
- Flat structure doesn't reflect physical architecture
- 8 migration-phase syncs no longer needed

---

## Target State

### New Folder Structure

```
portainer.stacks/
├── _shared/                          # Shared across all LXCs
│   └── docker-host-infra/
│
├── infra/                            # 192.168.0.112
│   ├── caddy/
│   ├── observability/
│   ├── infrastructure/
│   ├── cloudflare/
│   └── chatgpt/
│
├── media-gpu/                        # 192.168.0.212
│   ├── caddy/
│   ├── cloudflare-agent/
│   ├── arr/
│   ├── arr-gluetun/
│   ├── plex/
│   ├── jellyfin/
│   ├── emby/
│   ├── immich/
│   ├── audiobookshelf/
│   ├── komga/
│   ├── paperless/
│   ├── nut/
│   ├── stirling-pdf/
│   └── watchstate/
│
├── frigate-gpu/                      # 192.168.0.115
│   ├── caddy/
│   └── surveillance/
│
├── frigate/                          # 192.168.0.235
│   ├── caddy/
│   └── surveillance/
│
├── omada/                            # 192.168.0.238
│   ├── caddy/
│   └── omada/
│
└── komodo/                           # Komodo config (stays at root)
    ├── komodo.toml
    ├── core.config.toml
    └── MIGRATION/
```

### New ResourceSyncs (6 total)

| Sync Name | Tags | Description |
|-----------|------|-------------|
| `sync-foundation` | `foundation` | observability + caddy-infra (deploy first) |
| `sync-infra` | `infra` (exclude foundation) | infra server services |
| `sync-media-gpu` | `media-gpu` | media-gpu server services |
| `sync-frigate-gpu` | `frigate-gpu` | frigate-gpu server |
| `sync-frigate` | `frigate` | frigate production server |
| `sync-omada` | `omada` | omada server |

**Note:** `docker-host-infra-*` stacks use tag matching per-server, managed by respective per-LXC syncs.

---

## Implementation Steps

### Phase 1: Update Tags in komodo.toml

Add `foundation` tag to observability and caddy-infra stacks:
```toml
[[stack]]
name = "observability"
tags = ["foundation", "infra"]  # Add foundation

[[stack]]
name = "caddy-infra"
tags = ["foundation", "caddy", "infra"]  # Add foundation
```

### Phase 2: Move Folders

```bash
# Create LXC directories
mkdir -p portainer.stacks/{_shared,infra/caddy,media-gpu/caddy,frigate-gpu/caddy,frigate/caddy,omada/caddy}

# Move shared infrastructure
mv docker-host-infra _shared/

# Move infra stacks (caddy-infra is main instance with Dockerfile/.env)
mv observability infrastructure cloudflare chatgpt infra/
mv caddy/docker-compose-small.yml infra/caddy/docker-compose.yml
mv caddy/Dockerfile infra/caddy/
mv caddy/.env infra/caddy/

# Move media-gpu stacks (caddy-agent only, no Dockerfile needed)
mv arr arr-gluetun plex jellyfin emby immich audiobookshelf komga paperless nut stirling-pdf watchstate cloudflare-agent media-gpu/
mv caddy/docker-compose-big-media.yml media-gpu/caddy/docker-compose.yml

# Move frigate-gpu (caddy-agent only)
mv surveillance/frigate-gpu frigate-gpu/surveillance/
mv caddy/docker-compose-frigate-gpu.yml frigate-gpu/caddy/docker-compose.yml

# Move frigate (caddy-agent only)
mv surveillance/frigate frigate/surveillance/
mv caddy/docker-compose-frigate.yml frigate/caddy/docker-compose.yml

# Move omada (caddy-agent only)
mv omada omada/omada/
mv caddy/docker-compose-omada.yml omada/caddy/docker-compose.yml

# Verify all moved before cleanup
ls infra/caddy/docker-compose.yml infra/caddy/Dockerfile infra/caddy/.env
ls media-gpu/caddy/docker-compose.yml frigate-gpu/caddy/docker-compose.yml
ls frigate/caddy/docker-compose.yml omada/caddy/docker-compose.yml

# Cleanup old caddy folder (should be empty now)
rmdir caddy surveillance
```

**Note:** Only `infra/caddy` has the main Caddy instance (with Dockerfile/.env). Other LXCs run `caddy-agent` only (lightweight label watcher).

### Phase 3: Update komodo.toml Paths

Update all `run_directory` paths to match new structure:

```toml
# Before
run_directory = "portainer.stacks/arr"

# After
run_directory = "portainer.stacks/media-gpu/arr"
```

### Phase 4: Delete Old ResourceSyncs in Komodo UI

Remove phase-based syncs:
- phase1-foundation
- phase2-core
- phase3-caddy
- phase4-infra
- phase5-media-gpu
- phase6-frigate-gpu
- phase7-frigate
- phase8-omada

### Phase 5: Create New ResourceSyncs

**API Credentials:** Source from `komodo/MIGRATION/.env` (gitignored):
```bash
source MIGRATION/.env
# Sets: KOMODO_API_KEY, KOMODO_API_SECRET, KOMODO_URL
```

Create 6 new syncs via Komodo UI or API:

```bash
# sync-foundation
curl -X POST "$KOMODO_URL/write/CreateResourceSync" \
  -H "X-API-KEY: $KOMODO_API_KEY" -H "X-API-SECRET: $KOMODO_API_SECRET" \
  -d '{"name":"sync-foundation","config":{"match_tags":["foundation"]}}'

# sync-infra (exclude foundation)
curl -X POST "$KOMODO_URL/write/CreateResourceSync" \
  -d '{"name":"sync-infra","config":{"match_tags":["infra"],"exclude_tags":["foundation"]}}'

# ... repeat for other syncs
```

### Phase 6: Test Deployment

1. Push changes to git
2. Refresh each sync in Komodo UI
3. Verify pending changes look correct
4. Execute sync-foundation first
5. Execute remaining syncs

---

## Files to Modify

| File | Changes |
|------|---------|
| `komodo.toml` | Update all `run_directory` paths, add `foundation` tags |
| `service-map.md` | Update to reflect new structure |
| Folder structure | Move all stack folders |

## Safety Rules

**IMPORTANT: Before deleting anything, always verify files were copied/moved:**
```bash
# After each move, verify destination exists before removing source
ls -la <destination>  # Confirm files exist
# Only then proceed with cleanup
```

## Rollback Plan

If issues occur:
1. Git revert the folder moves
2. Restore old ResourceSyncs
3. Re-push to git

---

## Decisions Made

- **docker-host-infra**: Single `_shared/` folder, referenced by all 5 stacks
- **komodo/**: Stays at root level (master config, not tied to one LXC)
