https://docs.frigate.video/frigate/

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
FRIGATE_RTSP_PASSWORD=