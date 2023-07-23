# home.notavailable

this repo contains scripts used in my home automation

## garage.controller.api

### server.py
* runs on PiZero in the garage that has cloudflared tunnel and GSM hat
* triggers the garage door switch
* is called via HA REST action or IFTT action
* TODO: use HEAD as health probe in HA

### status.py
* TODO: checks status of door sensor, reports to status.api
* TODO: actionable notifications from HA

## garage.status.api
* runs in Docker in Portainer on Proxmox
* TODO: cloudflared tunnel, ingress via homeassistant instance
* TODO: HA has connected RESTful sensor to monitor state
* TODO: is updated from PiZero when garage door switch is triggered