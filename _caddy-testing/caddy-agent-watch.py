import docker
import requests
import os
import json
import threading
import logging
import signal
import sys
import time
import socket
from copy import deepcopy

# Configuration
AGENT_MODE = os.getenv("AGENT_MODE", "standalone")  # standalone, server, agent
AGENT_ID = os.getenv("AGENT_ID", socket.gethostname())
CADDY_API_URL = os.getenv("CADDY_API_URL", "http://caddy:2019")
CADDY_SERVER_URL = os.getenv("CADDY_SERVER_URL", "http://localhost:2019")  # For agent mode
CADDY_API_TOKEN = os.getenv("CADDY_API_TOKEN", "")
HOST_IP = os.getenv("HOST_IP", None)  # Will auto-detect if not set
DOCKER_LABEL_PREFIX = os.getenv("DOCKER_LABEL_PREFIX", "caddy")
AGENT_FILTER_LABEL = os.getenv("AGENT_FILTER_LABEL", None)  # Optional: filter containers by label (e.g., "agent=remote1")

client = docker.DockerClient(base_url='unix://var/run/docker.sock')

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def detect_host_ip():
    """Auto-detect host IP address"""
    try:
        # Try to get IP by connecting to a remote host (doesn't actually connect)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.warning(f"Failed to auto-detect host IP: {e}. Using 127.0.0.1")
        return "127.0.0.1"

def get_published_port(container, internal_port):
    """Get the published (host) port for a given container internal port"""
    try:
        ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
        port_key = f"{internal_port}/tcp"
        if port_key in ports and ports[port_key]:
            published = ports[port_key][0].get('HostPort')
            if published:
                return published

        # Fallback: check all ports for a match
        for key, bindings in ports.items():
            if bindings and key.startswith(str(internal_port)):
                return bindings[0].get('HostPort')

        logger.warning(f"No published port found for container {container.name} internal port {internal_port}")
        return None
    except Exception as e:
        logger.error(f"Error getting published port for {container.name}: {e}")
        return None

def get_target_caddy_url():
    """Get the target Caddy API URL based on mode"""
    if AGENT_MODE == "agent":
        return CADDY_SERVER_URL
    else:
        return CADDY_API_URL

def get_caddy_routes():
    """Get routes from Docker containers based on labels"""
    routes = []
    host_ip = HOST_IP or detect_host_ip() if AGENT_MODE == "agent" else None

    for container in client.containers.list():
        labels = container.attrs['Config']['Labels']
        if not labels:
            continue

        # Optional: filter containers by agent filter label
        if AGENT_FILTER_LABEL:
            filter_key, filter_value = AGENT_FILTER_LABEL.split("=", 1) if "=" in AGENT_FILTER_LABEL else (AGENT_FILTER_LABEL, None)
            container_filter_value = labels.get(filter_key)
            if not container_filter_value:
                continue  # Container doesn't have the filter label
            if filter_value and container_filter_value != filter_value:
                continue  # Container has the label but wrong value
            logger.debug(f"Container {container.name} matches filter {AGENT_FILTER_LABEL}")

        domain = labels.get(f"{DOCKER_LABEL_PREFIX}")
        proxy_target = labels.get(f"{DOCKER_LABEL_PREFIX}.reverse_proxy")

        # Support for {{upstreams PORT}} syntax
        import re
        upstreams_match = re.match(r"\{\{upstreams (\d+)}}", proxy_target.strip()) if proxy_target else None
        if upstreams_match:
            port = upstreams_match.group(1)
            try:
                # Agent mode: use host IP + published port
                if AGENT_MODE == "agent":
                    published_port = get_published_port(container, port)
                    if published_port and host_ip:
                        proxy_target = f"{host_ip}:{published_port}"
                        logger.info(f"[AGENT] Resolved {{upstreams {port}}} for domain '{domain}': {proxy_target}")
                    else:
                        logger.error(f"[AGENT] Cannot resolve upstream for {container.name}: port not published or host IP unavailable")
                        continue
                # Standalone/server mode: use container IP
                else:
                    network_settings = container.attrs.get('NetworkSettings', {})
                    networks = network_settings.get('Networks', {})
                    # Use the first network found
                    if networks:
                        ip = list(networks.values())[0].get('IPAddress')
                        if ip:
                            logger.info(f"Resolved {{upstreams {port}}} for domain '{domain}': {ip}:{port}")
                            proxy_target = f"{ip}:{port}"
                    if not proxy_target or proxy_target == labels.get(f"{DOCKER_LABEL_PREFIX}.reverse_proxy"):
                        logger.error(f"Failed to resolve {{upstreams {port}}} for {container.name}")
                        continue
            except Exception as e:
                logger.error(f"Failed to resolve {{upstreams {port}}} for {container.name}: {e}")
                continue

        if domain and proxy_target:
            logger.info(f"Route: domain '{domain}' will use upstream '{proxy_target}'")

            # Build route with agent metadata
            route = {
                "@id": f"{AGENT_ID}_{container.name}",
                "handle": [{
                    "handler": "reverse_proxy",
                    "upstreams": [{"dial": proxy_target}]
                }],
                "match": [{
                    "host": [domain]
                }]
            }
            routes.append(route)
    return routes

def push_to_caddy(routes):
    """Push routes to Caddy server based on mode"""
    target_url = get_target_caddy_url()

    # Build headers
    headers = {"Content-Type": "application/json"}
    if CADDY_API_TOKEN:
        headers["Authorization"] = f"Bearer {CADDY_API_TOKEN}"

    # Load local config
    config = load_local_config()

    # Ensure admin section is always present and accessible
    if "admin" not in config:
        config["admin"] = {}
    config["admin"]["listen"] = "0.0.0.0:2019"

    # Ensure apps structure exists
    if "apps" not in config:
        config["apps"] = {}
    if "http" not in config["apps"]:
        config["apps"]["http"] = {}
    if "servers" not in config["apps"]["http"]:
        config["apps"]["http"]["servers"] = {}
    if "reverse_proxy" not in config["apps"]["http"]["servers"]:
        config["apps"]["http"]["servers"]["reverse_proxy"] = {
            "listen": [":80"],
            "routes": []
        }

    # Merge routes
    local_routes = config["apps"]["http"]["servers"]["reverse_proxy"].get("routes", [])
    merged_routes = merge_routes(local_routes, routes)
    config["apps"]["http"]["servers"]["reverse_proxy"]["routes"] = merged_routes
    # Save updated config
    save_local_config(config)

    try:
        logger.info(f"Pushing config to {target_url} [Mode: {AGENT_MODE}]")
        response = requests.post(f"{target_url}/load", json=config, headers=headers)
        if response.status_code == 200:
            logger.info(f"✅ Caddy config updated successfully [Agent: {AGENT_ID}]")
        else:
            logger.error(f"❌ Caddy update failed: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Error pushing to Caddy: {e}")

    # Add a short delay to avoid hammering the Caddy API
    time.sleep(2)

def load_local_config():
    """Load local config or fetch from Caddy server"""
    # Always try to fetch current config from Caddy first to preserve routes from all agents
    target_url = get_target_caddy_url()
    try:
        headers = {}
        if CADDY_API_TOKEN:
            headers["Authorization"] = f"Bearer {CADDY_API_TOKEN}"

        response = requests.get(f"{target_url}/config/", headers=headers, timeout=5)
        if response.status_code == 200:
            config = response.json()
            logger.info("📥 Fetched existing config from Caddy")
            return config
    except Exception as e:
        logger.warning(f"Could not fetch existing config from Caddy: {e}")

    # Fallback: try to load cached config if fetch failed
    if os.path.exists("caddy-output.json"):
        try:
            with open("caddy-output.json", "r") as f:
                logger.info("📥 Using cached Caddy config (fetch failed)")
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to load cached Caddy config: {e}")

    # Return a new config structure with admin preserved
    return {
        "admin": {
            "listen": "0.0.0.0:2019"
        },
        "apps": {
            "http": {
                "servers": {
                    "reverse_proxy": {
                        "listen": [":80"],
                        "routes": []
                    }
                }
            }
        }
    }

def save_local_config(config):
    try:
        with open("caddy-output.json", "w") as f:
            json.dump(config, f, indent=2)
        logger.info("💾 Local copy of Caddy config saved to caddy-output.json")
    except Exception as e:
        logger.error(f"❌ Failed to save local Caddy config: {e}")

def merge_routes(local_routes, new_routes):
    """Merge local and new routes, using route ID and agent ID for tracking"""

    def get_route_id(route):
        """Get route ID, falling back to domain if no ID present"""
        if "@id" in route:
            return route["@id"]
        # Fallback to domain for routes without ID
        return route["match"][0]["host"][0] if route.get("match") and route["match"][0].get("host") else None

    def get_agent_id_from_route(route):
        """Extract agent ID from route ID"""
        route_id = get_route_id(route)
        if route_id and "_" in route_id:
            return route_id.split("_")[0]
        return None

    # Build dicts for fast lookup
    local_dict = {get_route_id(r): r for r in local_routes if get_route_id(r)}
    new_dict = {get_route_id(r): r for r in new_routes if get_route_id(r)}

    # Track changes
    added = []
    removed = []

    # Start with local routes, but only keep routes from other agents
    merged = {}
    for route_id, route in local_dict.items():
        agent_id = get_agent_id_from_route(route)
        # Keep routes from other agents or routes without agent ID
        if agent_id != AGENT_ID:
            merged[route_id] = route

    # Add/update routes from this agent
    for route_id, route in new_dict.items():
        if route_id not in local_dict:
            added.append(route_id)
        merged[route_id] = route

    # Track removed routes (only from this agent)
    for route_id in list(local_dict.keys()):
        agent_id = get_agent_id_from_route(local_dict[route_id])
        if agent_id == AGENT_ID and route_id not in new_dict:
            removed.append(route_id)

    if added:
        logger.info(f"Routes added: {added}")
    if removed:
        logger.info(f"Routes removed: {removed}")

    return list(merged.values())

def sync_config():
    logger.info("🔄 Syncing config...")
    routes = get_caddy_routes()
    push_to_caddy(routes)

last_update = 0
debounce_seconds = 5  # Increased debounce to 5 seconds

def watch_docker_events():
    logger.info("👀 Watching Docker events...")
    for event in client.events(decode=True):
        if event.get("Type") == "container":
            action = event.get("Action")
            if action in ["start", "stop", "die", "destroy"]:
                global last_update
                now = time.time()
                if now - last_update > debounce_seconds:
                    threading.Thread(target=sync_config).start()
                    last_update = now

def shutdown_handler(signum, frame):
    logger.info("Shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🚀 Caddy Docker Agent Starting")
    logger.info(f"   Mode: {AGENT_MODE}")
    logger.info(f"   Agent ID: {AGENT_ID}")
    logger.info(f"   Docker Label Prefix: {DOCKER_LABEL_PREFIX}")

    if AGENT_MODE == "agent":
        logger.info(f"   Target Server: {CADDY_SERVER_URL}")
        host_ip = HOST_IP or detect_host_ip()
        logger.info(f"   Host IP: {host_ip}")
    else:
        logger.info(f"   Caddy API: {CADDY_API_URL}")

    if CADDY_API_TOKEN:
        logger.info(f"   Authentication: Enabled (token configured)")
    else:
        logger.info(f"   Authentication: Disabled (no token)")

    if AGENT_FILTER_LABEL:
        logger.info(f"   Container Filter: {AGENT_FILTER_LABEL}")

    logger.info("="*60)

    sync_config()  # Initial sync
    watch_docker_events()
