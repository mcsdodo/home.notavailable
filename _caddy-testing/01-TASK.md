Caddy2 is a reverse proxy. Allows to be built with extensions.

# Current state
I use  following:
1. caddy-dns/cloudflare (see github.com/caddy-dns/cloudflare) for automatic DNS challenge certificate management
2. caddy-l4 (see github.com/caddyserver/caddy-l4) for TCP/UDP proxying - I'm using it for MQTT proxying.
3. lucaslorentz/caddy-docker-proxy/v2 (see github.com/lucaslorentz/caddy-docker-proxy) for automatic reverse proxying of docker containers.

# Desired state
The #3 allows to automatically create reverse proxy entries for docker containers based on their labels. The limitation is that it only works if the containers are on the same docker socket as Caddy itself. We need to build an extension that would allow to connect connect services to docker-proxy from other hosts.

1. it should work with labels
2. probably it should contain of a "server" caddy instance, that would run as in Current state and expose HTTP endpoints to register and an "client" caddy instance, that would run on other hosts and would report to the server instance about containers on the host via HTTP.
3. the proxying itself should be done by the server instance. The agent utilizes the docker socket to get container IPs and ports.


Suggest a solution. Search internet for similar setups or alternatives.
Suggest a testing setup with local docker compose / or multiple docker-composes to simulate multiple hosts.




