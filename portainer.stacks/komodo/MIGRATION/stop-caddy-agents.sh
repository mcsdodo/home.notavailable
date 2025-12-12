#!/bin/bash
# Stop caddy-agent containers on all hosts before phase 4
# This prevents conflicts when Komodo deploys new caddy stacks
#
# Usage:
#   ./stop-caddy-agents.sh           # Stop all caddy-agents
#   ./stop-caddy-agents.sh --status  # Just show status
#   ./stop-caddy-agents.sh --start   # Start them back up

set -euo pipefail

# All hosts
HOSTS=(
    "infra|192.168.0.112"
    "media-gpu|192.168.0.212"
    "frigate-gpu|192.168.0.115"
    "frigate|192.168.0.235"
    "omada|192.168.0.238"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

show_status() {
    echo -e "${CYAN}Caddy containers status:${NC}"
    echo ""
    for host in "${HOSTS[@]}"; do
        IFS='|' read -r name ip <<< "$host"
        echo -e "${YELLOW}=== $name ($ip) ===${NC}"
        ssh root@$ip "docker ps -a --filter name=caddy --format 'table {{.Names}}\t{{.Status}}'" 2>/dev/null || echo -e "${RED}Connection failed${NC}"
        echo ""
    done
}

stop_agents() {
    echo -e "${CYAN}Stopping and removing caddy-agent containers...${NC}"
    echo ""
    for host in "${HOSTS[@]}"; do
        IFS='|' read -r name ip <<< "$host"
        echo -e "${YELLOW}[$name] ${NC}Stopping caddy-agent on $ip..."

        # Stop container
        stop_result=$(ssh root@$ip "docker stop caddy-agent 2>&1" || true)

        if echo "$stop_result" | grep -q "No such container"; then
            echo -e "  ${YELLOW}○ Not running${NC}"
        elif echo "$stop_result" | grep -q "caddy-agent"; then
            echo -e "  ${GREEN}✓ Stopped${NC}"

            # Remove container
            echo -e "${YELLOW}[$name] ${NC}Removing caddy-agent on $ip..."
            rm_result=$(ssh root@$ip "docker rm caddy-agent 2>&1" || true)

            if echo "$rm_result" | grep -q "caddy-agent"; then
                echo -e "  ${GREEN}✓ Removed${NC}"
            else
                echo -e "  ${RED}✗ Remove error: $rm_result${NC}"
            fi
        else
            echo -e "  ${RED}✗ Error: $stop_result${NC}"
        fi
    done
    echo ""
    echo -e "${GREEN}Done! Caddy-agents stopped and removed on all hosts.${NC}"
}

start_agents() {
    echo -e "${CYAN}Starting caddy-agent containers...${NC}"
    echo ""
    for host in "${HOSTS[@]}"; do
        IFS='|' read -r name ip <<< "$host"
        echo -e "${YELLOW}[$name] ${NC}Starting caddy-agent on $ip..."

        result=$(ssh root@$ip "docker start caddy-agent 2>&1" || true)

        if echo "$result" | grep -q "No such container"; then
            echo -e "  ${YELLOW}○ Container doesn't exist${NC}"
        elif echo "$result" | grep -q "caddy-agent"; then
            echo -e "  ${GREEN}✓ Started${NC}"
        else
            echo -e "  ${RED}✗ Error: $result${NC}"
        fi
    done
    echo ""
    echo -e "${GREEN}Done! Caddy-agents started on all hosts.${NC}"
}

# Main
echo "═══════════════════════════════════════════════════════"
echo " Caddy-Agent Manager (Pre-Phase 4)"
echo "═══════════════════════════════════════════════════════"
echo ""

case "${1:-stop}" in
    --status|-s)
        show_status
        ;;
    --start)
        start_agents
        echo ""
        show_status
        ;;
    --stop|stop|"")
        stop_agents
        echo ""
        show_status
        ;;
    --help|-h)
        echo "Usage: $0 [--status|--stop|--start]"
        echo ""
        echo "Options:"
        echo "  --status  Show caddy container status on all hosts"
        echo "  --stop    Stop caddy-agent on all hosts (default)"
        echo "  --start   Start caddy-agent on all hosts"
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage"
        exit 1
        ;;
esac
