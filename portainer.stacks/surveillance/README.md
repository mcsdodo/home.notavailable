## Surveillance stack
[Frigate](https://docs.frigate.video/frigate/) is used as NVR, uses RTSP streams from Dahua cameras and Google Coral for object detection. Writes events to MQTT that runs on a remote site - therefore [Tailscale](https://tailscale.com/blog/docker-tailscale-guide) is used.

[Double-take](https://github.com/skrashevich/double-take) is used as UI for training and connecting [Compreface](https://github.com/exadel-inc/CompreFace) (on remote site - connected via Tailscale) for facial recognition. (see [docker-compose.yml](../surveillance-compreface/docker-compose.yml))

[frigate_plate_recognizer](https://github.com/ljmerza/frigate_plate_recognizer) listens on Frigate's MQTT topic to process _car_ objects and then runs [CodeprojectAI](https://www.codeproject.com/ai/docs/install/running_in_docker.html) (on a remote site - connected via Tailscale) for recognition. (see [docker-compose.yml](../surveillance-codeprojectai/docker-compose.yml))


https://community.home-assistant.io/t/google-coral-usb-frigate-proxmox/383737

`nano /etc/pve/lxc/XXX.conf`

```
lxc.cgroup2.devices.allow: c 226:0 rwm
lxc.cgroup2.devices.allow: c 226:128 rwm
lxc.cgroup2.devices.allow: c 29:0 rwm
lxc.cgroup2.devices.allow: c 189:* rwm
lxc.cgroup2.devices.allow: a
lxc.mount.entry: /dev/dri/renderD128 dev/dri/renderD128 none bind,optional,create=file 0, 0
lxc.mount.entry: /dev/bus/usb/002/ dev/bus/usb/002/ none bind,optional,create=dir 0, 0
lxc.mount.auto: cgroup:rw
```


## Env vars in portainer
FRIGATE_MQTT_USER=
FRIGATE_MQTT_PASSWORD=
FRIGATE_RTSP_CREDENTIALS=
TS_AUTHKEY= your tailscale auth key


## TODO:
- [ ] check https://github.com/kyle4269/frigate_alpr - it has UI
- [ ] actually do something with the detections (notification or whatever)