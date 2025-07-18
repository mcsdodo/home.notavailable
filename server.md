# Small server
* 100 - HaOS VM
* 101 - Cloudflared LXC
* 102 - MQTT LXC
* 103 - AdGuard LXC
* 105 - HaOS-dev VM
* 108 - Alpine Docker LXC running Portainer

# Big server
* 106 - AdGuard LXC
* 109 - Ubuntu VM
* 111 - TrueNAS VM
* 118 - Alpine Docker LXC runing Portainer

## Mounts 
``nano /etc/fstab``

192.168.0.101:/mnt/HD/HD_a2/Photos /mnt/pve/NotAvailableCldPhotos nfs nfsvers=3 0 0
192.168.0.101:/mnt/HD/HD_a2/Public /mnt/pve/NotAvailableCldPublic nfs nfsvers=3 0 0

https://community.home-assistant.io/t/google-coral-usb-frigate-proxmox/383737

Reload fstab
``mount -a``

## Pass USB coral to LXC

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

## Add ssh to Alpine LXC
```
apk add openssh &&
rc-update add sshd &&
rc-status &&
rc-service sshd start &&
mkdir ~/.ssh &&
chmod 700 ~/.ssh &&
cat /mnt/media/_tmp/id_rsa.pub >> ~/.ssh/authorized_keys &&
chmod 600 ~/.ssh/authorized_keys
```
