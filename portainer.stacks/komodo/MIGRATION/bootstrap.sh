#!/bin/bash
# Bootstrap Komodo ResourceSyncs from definitions
# Creates phased ResourceSyncs via Komodo API for incremental migration
#
# Usage:
#   ./bootstrap.sh                    # Create all ResourceSyncs
#   ./bootstrap.sh --phase 1          # Create only phase 1
#   ./bootstrap.sh --list             # List what would be created
#   ./bootstrap.sh --delete           # Delete all migration ResourceSyncs
#
# Prerequisites:
#   - KOMODO_API_KEY and KOMODO_API_SECRET environment variables set
#   - Komodo Core accessible at KOMODO_URL

set -euo pipefail

# Configuration
KOMODO_URL="${KOMODO_URL:-http://192.168.0.112:9120}"
KOMODO_API_KEY="${KOMODO_API_KEY:-}"
KOMODO_API_SECRET="${KOMODO_API_SECRET:-}"

# Git configuration
GIT_PROVIDER="github.com"
GIT_ACCOUNT="mcsdodo"
REPO="mcsdodo/home.notavailable"
BRANCH="${KOMODO_BRANCH:-feature/komodo}"
RESOURCE_PATH="portainer.stacks/komodo.toml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ResourceSync phases definition
# Format: "name|match_tags|exclude_tags|include_variables|description"
# exclude_tags: use "-" for none
# include_variables: true/false (only phase1 should sync variables)
PHASES=(
    "phase1-core-infra|core|-|true|Core infrastructure: alloy, watchtower, autoheal"
    "phase2-caddy-agents|caddy|core|false|Caddy reverse proxy agents"
    "phase3-infra-services|infra|core,caddy|false|Infra server: observability, cloudflare, chatgpt"
    "phase4-media-gpu|media-gpu|core,caddy|false|Media server: arr, plex, jellyfin, immich"
    "phase5-frigate-gpu|frigate-gpu|core,caddy|false|Frigate testing with GPU"
    "phase6-frigate|frigate|core,caddy|false|Frigate production with Coral"
    "phase7-omada|omada|core,caddy|false|Omada network controller"
)

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --phase N       Create only phase N (1-7)"
    echo "  --list          List ResourceSyncs that would be created"
    echo "  --delete        Delete all migration ResourceSyncs"
    echo "  --branch NAME   Override git branch (default: $BRANCH)"
    echo "  --dry-run       Show API calls without executing"
    echo "  --help          Show this help"
    echo ""
    echo "Environment variables:"
    echo "  KOMODO_URL          Komodo Core URL (default: $KOMODO_URL)"
    echo "  KOMODO_API_KEY      API key from Komodo UI"
    echo "  KOMODO_API_SECRET   API secret from Komodo UI"
    echo "  KOMODO_BRANCH       Git branch (default: feature/komodo)"
}

check_credentials() {
    if [[ -z "$KOMODO_API_KEY" || -z "$KOMODO_API_SECRET" ]]; then
        echo -e "${RED}Error: KOMODO_API_KEY and KOMODO_API_SECRET must be set${NC}"
        echo ""
        echo "Get these from Komodo UI: Settings → Users → API Keys"
        exit 1
    fi
}

# Make API request to Komodo
komodo_api() {
    local method=$1
    local endpoint=$2
    local data=${3:-}

    local response
    if [[ -n "$data" ]]; then
        response=$(curl -s -X "$method" "$KOMODO_URL/$endpoint" \
            -H "Content-Type: application/json" \
            -H "X-API-KEY: $KOMODO_API_KEY" \
            -H "X-API-SECRET: $KOMODO_API_SECRET" \
            -d "$data")
    else
        response=$(curl -s -X "$method" "$KOMODO_URL/$endpoint" \
            -H "X-API-KEY: $KOMODO_API_KEY" \
            -H "X-API-SECRET: $KOMODO_API_SECRET")
    fi
    echo "$response"
}

# Create a ResourceSync
create_resource_sync() {
    local name=$1
    local match_tags=$2
    local exclude_tags=$3
    local include_vars=$4
    local description=$5

    echo -e "${CYAN}Creating ResourceSync: $name${NC}"
    echo "  Match tags: $match_tags"
    [[ "$exclude_tags" != "-" ]] && echo "  Exclude tags: $exclude_tags"
    echo "  Include variables: $include_vars"
    echo "  Description: $description"

    # Build match_tags JSON array
    local match_json="[\"$match_tags\"]"

    # Build exclude_tags JSON array (or empty if "-")
    local exclude_json="[]"
    if [[ "$exclude_tags" != "-" ]]; then
        # Convert comma-separated to JSON array
        exclude_json="[$(echo "$exclude_tags" | sed 's/,/","/g' | sed 's/^/"/;s/$/"/')]"
    fi

    # Build include_variables boolean
    local include_vars_json="false"
    [[ "$include_vars" == "true" ]] && include_vars_json="true"

    local payload=$(cat <<EOF
{
    "name": "$name",
    "config": {
        "repo": "$REPO",
        "branch": "$BRANCH",
        "resource_path": ["$RESOURCE_PATH"],
        "git_provider": "$GIT_PROVIDER",
        "git_account": "$GIT_ACCOUNT",
        "match_tags": $match_json,
        "exclude_tags": $exclude_json,
        "include_variables": $include_vars_json,
        "include_resources": true
    },
    "description": "$description"
}
EOF
)

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY RUN] Would POST to /write/CreateResourceSync:${NC}"
        echo "$payload" | jq . 2>/dev/null || echo "$payload"
        return
    fi

    local response=$(komodo_api "POST" "write/CreateResourceSync" "$payload")

    if echo "$response" | grep -q '"_id"'; then
        echo -e "${GREEN}  ✓ Created successfully${NC}"
    else
        echo -e "${RED}  ✗ Failed: $response${NC}"
    fi
}

# List all ResourceSyncs
list_syncs() {
    echo -e "${CYAN}ResourceSyncs that would be created:${NC}"
    echo ""
    local i=1
    for phase in "${PHASES[@]}"; do
        IFS='|' read -r name match_tags exclude_tags include_vars desc <<< "$phase"
        echo "Phase $i: $name"
        echo "  Match tags: $match_tags"
        [[ "$exclude_tags" != "-" ]] && echo "  Exclude tags: $exclude_tags"
        echo "  Include variables: $include_vars"
        echo "  Description: $desc"
        echo ""
        ((i++))
    done
}

# Delete migration ResourceSyncs
delete_syncs() {
    echo -e "${YELLOW}Deleting migration ResourceSyncs...${NC}"

    for phase in "${PHASES[@]}"; do
        IFS='|' read -r name match_tags exclude_tags include_vars desc <<< "$phase"
        echo -e "${CYAN}Deleting: $name${NC}"

        if [[ "$DRY_RUN" == "true" ]]; then
            echo -e "${YELLOW}[DRY RUN] Would DELETE $name${NC}"
            continue
        fi

        # First get the ID
        local list_response=$(komodo_api "POST" "read/ListResourceSyncs" "{}")
        local sync_id=$(echo "$list_response" | grep -o "\"id\":\"[^\"]*\",\"type\":\"ResourceSync\",\"name\":\"$name\"" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

        if [[ -z "$sync_id" ]]; then
            echo -e "${YELLOW}  - Not found (already deleted?)${NC}"
            continue
        fi

        local response=$(komodo_api "POST" "write/DeleteResourceSync" "{\"id\": \"$sync_id\"}")

        if echo "$response" | grep -q '"_id"'; then
            echo -e "${GREEN}  ✓ Deleted${NC}"
        else
            echo -e "${RED}  ✗ Failed: $response${NC}"
        fi
    done
}

# Main
DRY_RUN="false"
PHASE_FILTER=""
ACTION="create"

while [[ $# -gt 0 ]]; do
    case $1 in
        --phase)
            PHASE_FILTER="$2"
            shift 2
            ;;
        --list)
            ACTION="list"
            shift
            ;;
        --delete)
            ACTION="delete"
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

echo "═══════════════════════════════════════════════════════"
echo " Komodo ResourceSync Bootstrap"
echo "═══════════════════════════════════════════════════════"
echo "URL:    $KOMODO_URL"
echo "Branch: $BRANCH"
echo "Action: $ACTION"
[[ "$DRY_RUN" == "true" ]] && echo -e "${YELLOW}DRY RUN MODE${NC}"
echo ""

case $ACTION in
    list)
        list_syncs
        ;;
    delete)
        check_credentials
        delete_syncs
        ;;
    create)
        check_credentials

        if [[ -n "$PHASE_FILTER" ]]; then
            # Create single phase
            idx=$((PHASE_FILTER - 1))
            if [[ $idx -lt 0 || $idx -ge ${#PHASES[@]} ]]; then
                echo -e "${RED}Invalid phase: $PHASE_FILTER (must be 1-${#PHASES[@]})${NC}"
                exit 1
            fi
            IFS='|' read -r name match_tags exclude_tags include_vars desc <<< "${PHASES[$idx]}"
            create_resource_sync "$name" "$match_tags" "$exclude_tags" "$include_vars" "$desc"
        else
            # Create all phases
            echo "Creating ${#PHASES[@]} ResourceSyncs..."
            echo ""
            for phase in "${PHASES[@]}"; do
                IFS='|' read -r name match_tags exclude_tags include_vars desc <<< "$phase"
                create_resource_sync "$name" "$match_tags" "$exclude_tags" "$include_vars" "$desc"
                echo ""
            done
        fi

        echo ""
        echo -e "${GREEN}Done!${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Open Komodo UI: $KOMODO_URL"
        echo "2. Go to Resource Syncs"
        echo "3. Click 'Refresh' on each sync to see pending changes"
        echo "4. Review and 'Execute' to deploy"
        ;;
esac
