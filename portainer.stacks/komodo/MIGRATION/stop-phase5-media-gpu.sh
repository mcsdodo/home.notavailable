#!/bin/bash
# Stop and remove media-gpu containers before phase 5
# Stacks: arr, arr-gluetun, plex, jellyfin, emby, immich, audiobookshelf, komga, paperless, nut, stirling-pdf, watchstate, cloudflare-agent
#
# Usage:
#   ./stop-phase5-media-gpu.sh           # Stop and remove
#   ./stop-phase5-media-gpu.sh --status  # Just show status

set -euo pipefail

HOST="192.168.0.212"
HOST_NAME="media-gpu"

# Containers to stop/remove (actual names from docker ps)
CONTAINERS=(
    # arr stack (prefixed with arr-)
    "arr-sonarr-1"
    "arr-radarr-1"
    "arr-overseerr-1"
    "arr-sabnzbd-1"
    "arr-mylar3-1"
    "decluttarr"
    "jellyseerr"
    # arr-gluetun stack (prefixed with arr-gluetun-)
    "arr-gluetun-gluetun-1"
    "arr-gluetun-prowlarr-1"
    "arr-gluetun-bazarr-1"
    "arr-gluetun-qbittorrent-1"
    # plex
    "plex"
    # jellyfin
    "jellyfin"
    "jellyfin-scheduled-restarts-1"
    # emby
    "embyserver"
    "emby-scheduled-restarts-1"
    # immich
    "immich-server"
    "immich-machine-learning"
    "immich-postgres"
    "immich-redis"
    # audiobookshelf
    "audiobookshelf"
    # komga
    "komga"
    # paperless (prefixed)
    "paperless-webserver-1"
    "paperless-db-1"
    "paperless-broker-1"
    # nut
    "peanut"
    # stirling-pdf
    "stirling-pdf"
    # watchstate
    "watchstate"
    # cloudflare-agent
    "dockflare-agent"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

show_status() {
    echo -e "${CYAN}Phase 5 containers status on $HOST_NAME ($HOST):${NC}"
    echo ""
    for container in "${CONTAINERS[@]}"; do
        status=$(ssh root@$HOST "docker ps -a --filter name=^${container}$ --format '{{.Status}}'" 2>/dev/null || echo "error")
        if [[ -z "$status" ]]; then
            echo -e "  ${YELLOW}○${NC} $container - not found"
        elif [[ "$status" == "error" ]]; then
            echo -e "  ${RED}✗${NC} $container - connection error"
        elif echo "$status" | grep -q "Up"; then
            echo -e "  ${GREEN}●${NC} $container - running"
        else
            echo -e "  ${RED}○${NC} $container - stopped"
        fi
    done
}

stop_and_remove() {
    echo -e "${CYAN}Stopping and removing phase 5 containers on $HOST_NAME ($HOST)...${NC}"
    echo ""

    local success=0
    local skipped=0
    local failed=0

    for container in "${CONTAINERS[@]}"; do
        # Stop
        stop_result=$(ssh root@$HOST "docker stop $container 2>&1" || true)
        if echo "$stop_result" | grep -q "No such container"; then
            ((skipped++)) || true
            continue
        elif echo "$stop_result" | grep -q "$container"; then
            # Remove
            rm_result=$(ssh root@$HOST "docker rm $container 2>&1" || true)
            if echo "$rm_result" | grep -q "$container"; then
                echo -e "  ${GREEN}✓${NC} $container"
                ((success++)) || true
            else
                echo -e "  ${RED}✗${NC} $container - remove failed"
                ((failed++)) || true
            fi
        else
            echo -e "  ${RED}✗${NC} $container - stop failed"
            ((failed++)) || true
        fi
    done

    echo ""
    echo -e "${GREEN}Done!${NC} Removed: $success, Skipped: $skipped, Failed: $failed"
}

# Main
echo "═══════════════════════════════════════════════════════"
echo " Phase 5: Media-GPU Services"
echo "═══════════════════════════════════════════════════════"
echo ""

case "${1:-stop}" in
    --status|-s)
        show_status
        ;;
    --stop|stop|"")
        stop_and_remove
        ;;
    --help|-h)
        echo "Usage: $0 [--status|--stop]"
        ;;
    *)
        echo "Unknown option: $1"
        exit 1
        ;;
esac
