# home.notavailable

this repo contains scripts and apps used in my garage automation

## PiZero apps (garage)

### controller.api.py
- [x] runs on PiZero in the garage that has cloudflared tunnel and GSM hat
- [x] triggers the garage door switch
- [x] is called via HA REST action or IFTT action
- [x] open garage from from Garmin watch (see https://github.com/hatl/hasscontrol)

### status.service.py
- [x] checks status of door sensor, reports to status.api
- [x] reports health to status.api
- [x] redeploy all above apps to PiZero 
- [x] install door sensor
- [ ] ~~run Docker/Compose? on PiZero, update apps on-demand remotely somehow~~
- [ ] ~~measure how much data would above solution consume per-update~~
- [ ] update via API call and ``git pull``

## Docker apps (home Proxmox)

### garage.status.api
- [x] runs in Docker in Portainer on Proxmox
- [x] github action with push to docker.io
- [x] cloudflared tunnel, ingress via homeassistant instance
- [x] use containrrr/watchtower to auto recreate container when newer version is pushed
- [x] HA has connected RESTful sensor to monitor state
- [x] is updated from PiZero when garage door switch is triggered and/or state changes
- [x] report UNKNOWN after a defined period of unavailability

### Home Assistant
- [ ] actionable notifications from HA when garage door is opened for longer than set time. Basically whenever status.api gets 'OPENED' update, trigger a notification.
- [ ] is it possible to ditch IFTT and control HA directly from Google voice assitant? https://www.makeuseof.com/home-assistant-use-with-google-home-voice-assistant/ Maybe even to ask "Is my garage closed?"

## General todos
- [ ] try out https://github.com/codenio/mock.gpio

https://raspi.tv/2013/rpi-gpio-basics-7-rpi-gpio-cheat-sheet-and-pointers-to-rpi-gpio-advanced-tutorials#top
https://create.withcode.uk/python/A3
