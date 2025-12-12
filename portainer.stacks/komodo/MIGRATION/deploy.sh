#!/bin/bash
# Deploy stacks directly to Komodo (dev workflow - bypasses git)
#
# During development, deploy stacks directly via Komodo API instead of
# waiting for git push + ResourceSync. This allows rapid iteration.
#
# Production workflow: git push → ResourceSync → deploy
# Development workflow: ./deploy.sh <stack> → direct API deploy
#
# Usage:
#   ./deploy.sh <stack-name>           Deploy single stack
#   ./deploy.sh --all                  Deploy all stacks
#   ./deploy.sh --all --server <name>  Deploy all stacks on server
#   ./deploy.sh --list                 List available stacks
#   ./deploy.sh --status               Show stack status
#   ./deploy.sh --dry-run <stack>      Preview without deploying

set -euo pipefail

# Configuration
KOMODO_URL="${KOMODO_URL:-http://192.168.0.112:9120}"
KOMODO_API_KEY="${KOMODO_API_KEY:-}"
KOMODO_API_SECRET="${KOMODO_API_SECRET:-}"

# Path to komodo.toml
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KOMODO_TOML="$SCRIPT_DIR/../komodo.toml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

DRY_RUN="false"

usage() {
    echo "Usage: $0 [OPTIONS] [STACK_NAME]"
    echo ""
    echo "Options:"
    echo "  --all             Deploy all stacks"
    echo "  --server NAME     Filter by server (with --all)"
    echo "  --list            List available stacks"
    echo "  --status          Show stack status"
    echo "  --dry-run         Preview without deploying"
    echo "  --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 surveillance-testing        Deploy single stack"
    echo "  $0 --all --server frigate-gpu  Deploy all on server"
    echo "  $0 --list                      List available stacks"
}

check_credentials() {
    if [[ -z "$KOMODO_API_KEY" || -z "$KOMODO_API_SECRET" ]]; then
        echo -e "${RED}Error: KOMODO_API_KEY and KOMODO_API_SECRET must be set${NC}"
        echo ""
        echo "Get these from Komodo UI: Settings → Users → API Keys"
        exit 1
    fi
}

# Make API request
komodo_api() {
    local method=$1
    local endpoint=$2
    local data=${3:-}

    if [[ -n "$data" ]]; then
        curl -s -X "$method" "$KOMODO_URL/$endpoint" \
            -H "Content-Type: application/json" \
            -H "X-API-KEY: $KOMODO_API_KEY" \
            -H "X-API-SECRET: $KOMODO_API_SECRET" \
            -d "$data"
    else
        curl -s -X "$method" "$KOMODO_URL/$endpoint" \
            -H "X-API-KEY: $KOMODO_API_KEY" \
            -H "X-API-SECRET: $KOMODO_API_SECRET"
    fi
}

# Get stacks from komodo.toml
get_stacks() {
    local server_filter=${1:-}

    if [[ ! -f "$KOMODO_TOML" ]]; then
        echo -e "${RED}Error: komodo.toml not found at $KOMODO_TOML${NC}" >&2
        exit 1
    fi

    # Extract stack names and server_ids using grep/awk
    awk '
        /^\[\[stack\]\]/ { in_stack=1; name=""; server="" }
        in_stack && /^name\s*=/ { gsub(/.*=\s*"|"/, ""); name=$0 }
        in_stack && /^server_id\s*=/ { gsub(/.*=\s*"|"/, ""); server=$0 }
        in_stack && /^\[/ && !/^\[\[stack\]\]/ {
            if (name != "") print name "|" server
            in_stack=0
        }
        END { if (in_stack && name != "") print name "|" server }
    ' "$KOMODO_TOML" | while IFS='|' read -r name server; do
        if [[ -z "$server_filter" || "$server" == "$server_filter" ]]; then
            echo "$name|$server"
        fi
    done
}

# List stacks
list_stacks() {
    echo -e "${CYAN}Available Stacks in komodo.toml:${NC}"
    echo ""

    local current_server=""
    get_stacks | sort -t'|' -k2,2 -k1,1 | while IFS='|' read -r name server; do
        if [[ "$server" != "$current_server" ]]; then
            [[ -n "$current_server" ]] && echo ""
            echo -e "${YELLOW}═══ $server ═══${NC}"
            current_server="$server"
        fi
        echo "  $name"
    done

    echo ""
    local count=$(get_stacks | wc -l)
    echo -e "${GREEN}Total: $count stacks${NC}"
}

# Deploy a stack
deploy_stack() {
    local stack_name=$1

    echo -e "${CYAN}Deploying $stack_name...${NC}"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY RUN] Would deploy: $stack_name${NC}"
        return 0
    fi

    local response=$(komodo_api "POST" "execute/DeployStack" "{\"stack\": \"$stack_name\"}")

    if echo "$response" | grep -qE '"ok"|"success"'; then
        echo -e "${GREEN}  ✓ Deployed: $stack_name${NC}"
        return 0
    else
        echo -e "${RED}  ✗ Failed: $stack_name${NC}"
        echo -e "${GRAY}  $response${NC}"
        return 1
    fi
}

# Show stack status
show_status() {
    echo -e "${CYAN}Fetching stack status from Komodo...${NC}"
    echo ""

    local response=$(komodo_api "POST" "read/ListStacks" "{}")

    if command -v jq &> /dev/null; then
        echo "$response" | jq -r '.[] | "\(.info.state // "Unknown")|\(.name)|\(.config.server_id)"' | \
            sort -t'|' -k3,3 -k2,2 | while IFS='|' read -r state name server; do
                case "$state" in
                    Running) echo -e "${GREEN}  ✓${NC} $name ${GRAY}($server)${NC}" ;;
                    Stopped) echo -e "${YELLOW}  ○${NC} $name ${GRAY}($server)${NC}" ;;
                    *)       echo -e "${GRAY}  ?${NC} $name ${GRAY}($server)${NC}" ;;
                esac
            done
    else
        echo "$response"
    fi
}

# Main
echo "═══════════════════════════════════════════════════════"
echo " Komodo Stack Deployer (Dev Workflow)"
echo "═══════════════════════════════════════════════════════"
echo -e "${GRAY}URL: $KOMODO_URL${NC}"

ACTION=""
SERVER_FILTER=""
STACK_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            ACTION="all"
            shift
            ;;
        --server)
            SERVER_FILTER="$2"
            shift 2
            ;;
        --list)
            ACTION="list"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            STACK_NAME="$1"
            ACTION="single"
            shift
            ;;
    esac
done

[[ "$DRY_RUN" == "true" ]] && echo -e "${YELLOW}MODE: DRY RUN${NC}"
echo ""

case "$ACTION" in
    list)
        list_stacks
        ;;
    status)
        check_credentials
        show_status
        ;;
    all)
        check_credentials
        echo -e "${CYAN}Deploying all stacks${SERVER_FILTER:+ on $SERVER_FILTER}...${NC}"
        echo ""

        success=0
        failed=0

        while IFS='|' read -r name server; do
            if deploy_stack "$name"; then
                ((success++))
            else
                ((failed++))
            fi
        done < <(get_stacks "$SERVER_FILTER")

        echo ""
        if [[ $failed -eq 0 ]]; then
            echo -e "${GREEN}Results: $success succeeded, $failed failed${NC}"
        else
            echo -e "${YELLOW}Results: $success succeeded, $failed failed${NC}"
        fi
        ;;
    single)
        check_credentials
        deploy_stack "$STACK_NAME"
        ;;
    *)
        usage
        ;;
esac
