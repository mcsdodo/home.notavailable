# home.notavailable

this repo contains scripts used in my home automation

## garage.controller.api

### server.py
- [x] runs on PiZero in the garage that has cloudflared tunnel and GSM hat
- [x] triggers the garage door switch
- [x] is called via HA REST action or IFTT action
- [ ] use HEAD as health probe in HA

### status.py
- [ ] checks status of door sensor, reports to status.api
- [ ] actionable notifications from HA

## garage.status.api
- [x] runs in Docker in Portainer on Proxmox
- [x] github action with push to docker.io
- [x] cloudflared tunnel, ingress via homeassistant instance
- [ ] HA has connected RESTful sensor to monitor state
- [ ] is updated from PiZero when garage door switch is triggered and/or state changes