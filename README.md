# home.notavailable

this repo contains scripts used in my home automation

## garage.controller.api

### controller.api.py
- [x] runs on PiZero in the garage that has cloudflared tunnel and GSM hat
- [x] triggers the garage door switch
- [x] is called via HA REST action or IFTT action
- [x] open garage from from Garmin watch (see https://github.com/hatl/hasscontrol)
- [x] use HEAD as /healtz probe in HA

### status.service.py
- [x] checks status of door sensor, reports to status.api
- [ ] actionable notifications from HA when garage door is opened for longer than set time

## garage.status.api
- [x] runs in Docker in Portainer on Proxmox
- [x] github action with push to docker.io
- [x] cloudflared tunnel, ingress via homeassistant instance
- [x] use containrrr/watchtower to auto recreate container when newer version is pushed
- [x] HA has connected RESTful sensor to monitor state
- [x] is updated from PiZero when garage door switch is triggered and/or state changes
- [x] report UNKNOWN after a defined period of unavailability
- [ ] figure how to convert utc time to local time in HA dashboard tile
- [ ] redeploy all above applicable to PiZero (& install sensor)


# https://raspi.tv/2013/rpi-gpio-basics-7-rpi-gpio-cheat-sheet-and-pointers-to-rpi-gpio-advanced-tutorials#top
# https://create.withcode.uk/python/A3
