# garage.controller.api

## server.py
* runs on PiZero in the garage that has cloudflared tunnel
* triggers the garage door switch
* is called via HA REST action or IFTT action

## status.py
* checks status, reports to status.api
* sends livez

# garage.status.api
* runs in Docker in Portainer on Proxmox, cloudflared tunnel via homeassistant instance
* HA has connected RESTful sensor to monitor state
* is updated from PiZero when garage door switch is triggered