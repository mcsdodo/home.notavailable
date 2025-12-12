#!/bin/bash
# Stop and remove frigate-gpu containers before phase 6
# Stacks: surveillance-testing
#
# Usage:
#   ./stop-phase6-frigate-gpu.sh           # Stop and remove
#   ./stop-phase6-frigate-gpu.sh --status  # Just show status

set -euo pipefail

HOST="192.168.0.115"
HOST_NAME="frigate-gpu"

# Containers to stop/remove (actual names from docker ps)
CONTAINERS=(
    "surveillance-frigate-testing"
    "surveillance-mqtt-1"
    "surveillance-restart-frigate-1"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

show_status() {
    echo -e "${CYAN}Phase 6 containers status on $HOST_NAME ($HOST):${NC}"
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
    echo -e "${CYAN}Stopping and removing phase 6 containers on $HOST_NAME ($HOST)...${NC}"
    echo ""

    for container in "${CONTAINERS[@]}"; do
        echo -e "${YELLOW}[$container]${NC}"

        stop_result=$(ssh root@$HOST "docker stop $container 2>&1" || true)
        if echo "$stop_result" | grep -q "No such container"; then
            echo -e "  ${YELLOW}○ Not found${NC}"
            continue
        elif echo "$stop_result" | grep -q "$container"; then
            echo -e "  ${GREEN}✓ Stopped${NC}"
        else
            echo -e "  ${RED}✗ Stop error${NC}"
            continue
        fi

        rm_result=$(ssh root@$HOST "docker rm $container 2>&1" || true)
        if echo "$rm_result" | grep -q "$container"; then
            echo -e "  ${GREEN}✓ Removed${NC}"
        else
            echo -e "  ${RED}✗ Remove error${NC}"
        fi
    done

    echo ""
    echo -e "${GREEN}Done!${NC}"
}

# Main
echo "═══════════════════════════════════════════════════════"
echo " Phase 6: Frigate-GPU (surveillance-testing)"
echo "═══════════════════════════════════════════════════════"
echo ""

case "${1:-stop}" in
    --status|-s)
        show_status
        ;;
    --stop|stop|"")
        stop_and_remove
        echo ""
        show_status
        ;;
    --help|-h)
        echo "Usage: $0 [--status|--stop]"
        ;;
    *)
        echo "Unknown option: $1"
        exit 1
        ;;
esac
