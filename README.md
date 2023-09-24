# home.notavailable

this repo contains scripts and apps used in my garage automation. Current garage runs a RpiZeroW with GSM hat & relay & 4G Wifi router. 

## v1
First version did use GSM hat for internet connection, Cloudflare for tunneling and internet access. Software-wise a [simple API](./garage.controller.api/) to trigger relay and open a garage.

## v1.1
Added a [status.service](./garage.controller.api/status.service.py) that reports health and state to [my home server](./garage.status.api/status.api.py) when garage door moves. Home server is then used for Homeassistant integration.

## v2
There is a ramp leading to garages in our apartment building that requires a phone call to operate. It is a cumbersome operation ideal for an automation (who wants to make calls when you can call an API?). Making Raspberry to use GSM hat for permanent internet connection AND to perform calls to the ramp proved time consuming (in terms of research). I'm using a cheap 4G WiFi modem for internet connection and GSM hat to make calls.

## PiZero apps (garage) checklist & worklog

### controller.api.py
- [x] runs on PiZero in the garage that has cloudflared tunnel and GSM hat
- [x] triggers the garage door switch
- [x] is called via HA REST action or IFTT action
- [x] open garage from from Garmin watch (see https://github.com/hatl/hasscontrol)
- [ ] abandon cloudflared on PiZero - make calls from Homelab -> PiZero via Tailscale (seems to be lot less data consuming than keeping Cloudflared tunnel open)

### status.service.py
- [x] checks status of door sensor, reports to status.api
- [x] reports health to status.api
- [x] redeploy all above apps to PiZero 
- [x] install door sensor
- [ ] ~~run Docker/Compose? on PiZero, update apps on-demand remotely somehow~~
- [ ] ~~measure how much data would above solution consume per-update~~
- [x] update via API call and ``git pull``

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
- [x] actionable notifications from HA when garage door is opened for longer than set time. Basically whenever status.api gets 'OPENED' update, trigger a notification. [See here](/homeassistant/garage.notification.yml)
- [ ] is it possible to ditch IFTT and control HA directly from Google voice assitant? https://www.makeuseof.com/home-assistant-use-with-google-home-voice-assistant/ Maybe even to ask "Is my garage closed?"
- [ ] store configuration / automations / scripts on github and update automatically
- [x] repeat 'Garage is opened' notification every 5 minutes after initial notification (only if still opened)
- [x] access Eufy security camera stream over Tailscale private network from HA instance at home <> 4G router in garage https://github.com/fuatakgun/eufy_security/issues/935

## General todos
- [ ] ~~try out https://github.com/codenio/mock.gpio~~

https://raspi.tv/2013/rpi-gpio-basics-7-rpi-gpio-cheat-sheet-and-pointers-to-rpi-gpio-advanced-tutorials#top
https://create.withcode.uk/python/A3
