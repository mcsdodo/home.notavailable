#!/bin/bash
# Extract environment variables from all running containers across all servers
# Usage: ./extract-secrets.sh [--output secrets.env] [--server <server-name>]
#
# This script SSHs to each Portainer LXC and extracts environment variables
# from running containers using docker inspect.
#
# Output is saved to secrets.env (or specified file) in KEY=VALUE format
# Sensitive values are included - DELETE FILE AFTER USE

set -euo pipefail

# Server definitions
declare -A SERVERS=(
    ["infra"]="192.168.0.112"
    ["media-gpu"]="192.168.0.212"
    ["frigate-gpu"]="192.168.0.115"
    ["frigate"]="192.168.0.235"
    ["omada"]="192.168.0.238"
)

# Default output file
OUTPUT_FILE="secrets.env"
TARGET_SERVER=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output|-o)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --server|-s)
            TARGET_SERVER="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--output secrets.env] [--server <server-name>]"
            echo ""
            echo "Servers: ${!SERVERS[*]}"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to extract env vars from a server
extract_from_server() {
    local name=$1
    local ip=$2

    echo "# ============================================="
    echo "# Server: $name ($ip)"
    echo "# ============================================="

    # Get all running containers and their env vars
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "root@$ip" 2>/dev/null << 'REMOTE_SCRIPT'
for container in $(docker ps --format '{{.Names}}'); do
    # Get compose project (stack name)
    stack=$(docker inspect --format='{{index .Config.Labels "com.docker.compose.project"}}' "$container" 2>/dev/null || echo "standalone")

    echo ""
    echo "# --- Container: $container (Stack: $stack) ---"

    # Get environment variables, filter out common non-secret ones
    docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container" 2>/dev/null | \
        grep -vE '^(PATH=|HOME=|HOSTNAME=|LANG=|LC_|TERM=|SHLVL=|PWD=|_=|container=|NVIDIA_|CUDA_|LD_LIBRARY_PATH=|PUID=|PGID=|TZ=|UMASK=)' | \
        sort
done
REMOTE_SCRIPT
}

# Main execution
{
    echo "# Komodo Migration - Extracted Environment Variables"
    echo "# Generated: $(date)"
    echo "# WARNING: Contains sensitive data - DELETE AFTER USE"
    echo ""

    if [[ -n "$TARGET_SERVER" ]]; then
        # Single server
        if [[ -v "SERVERS[$TARGET_SERVER]" ]]; then
            extract_from_server "$TARGET_SERVER" "${SERVERS[$TARGET_SERVER]}"
        else
            echo "Error: Unknown server '$TARGET_SERVER'" >&2
            echo "Available: ${!SERVERS[*]}" >&2
            exit 1
        fi
    else
        # All servers
        for server in "${!SERVERS[@]}"; do
            extract_from_server "$server" "${SERVERS[$server]}"
            echo ""
        done
    fi
} > "$OUTPUT_FILE"

echo "Secrets extracted to: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo "1. Review $OUTPUT_FILE and identify secrets needed for Komodo"
echo "2. Add secrets to core.config.toml [secrets] section"
echo "3. DELETE $OUTPUT_FILE when done (contains sensitive data)"
