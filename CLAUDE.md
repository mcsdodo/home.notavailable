** IMPORTANT **
DO NOT ever commit and push without being asked to do so.

# Passwordless ssh to portiainer LXC instances

Multiple LXCs on multiple physical hosts.

## Host1 small-main
Main mini PC with caddy, observability, networking etc.
- Main Caddy LXC `ssh root@192.168.0.20` with *.lan and layer4 caddy. "Bare metal" - not docker.
- Portainer LXC1 (infra) `ssh root@192.168.0.112`
       - caddy here runs with macvlan on `192.168.0.21` - this one handles *.lacny.me

## Host2 - big-gpu
Big server with NVIDIA GPU, running media server, truenas etc.
- Portainer agent LXC2 (media-gpu) `ssh root@192.168.0.212`
- Portainer agent LXC3 (frigate-gpu) `ssh@192.168.0.115`

## Host3 small-frigate
Mini PC with frigate + omada
- Portainer agent LXC4 (frigate) `ssh@192.168.0.235`
- Portainer agent LXC5 (omada) `ssh@192.168.0.238`


# Cloudflare zones:
| Zone            | Zone ID                          |
|-----------------|----------------------------------|
| lacny.me        | 77e2ac28cf937e13ac966711fb95f0b4 |
| notavailable.uk | 7041901e877a5002678a7db3678ec3d7 |
| 173591.xyz      | 2f5ac21d4dbfdb6599ab60a4ddbee435 |