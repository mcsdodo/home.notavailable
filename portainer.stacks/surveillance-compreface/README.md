## Set folowing ENV vars in portainer
postgres_username=
postgres_password=


## Nvidia GPU passthrough to LXC and Docker
Proxmox with secure boot did not work for me. I had it disabled in BIOS prior all this worked.
[Original source here](https://theorangeone.net/posts/lxc-nvidia-gpu-passthrough/)

### Host setup
1. install drivers on host. Download .run file, e.g. `wget https://international.download.nvidia.com/XFree86/Linux-x86_64/550.127.05/NVIDIA-Linux-x86_64-550.127.05.run`. `chmod +x NVIDIA-Linux-x86_64-550.127.05.run` and run it `./NVIDIA-Linux-x86_64-550.127.05.run`.
2. add following to `/etc/modules-load.d/modules.conf`
```
# Nvidia modules
nvidia
nvidia_uvm
```
3. run `update-initramfs -u -k all`
4. following to `/etc/udev/rules.d/70-nvidia.rules`
```
KERNEL=="nvidia", RUN+="/bin/bash -c '/usr/bin/nvidia-smi -L && /bin/chmod 666 /dev/nvidia*'"
KERNEL=="nvidia_uvm", RUN+="/bin/bash -c '/usr/bin/nvidia-modprobe -c0 -u && /bin/chmod 0666 /dev/nvidia-uvm*'"
```
5. reboot. `nvidia-smi` should return something like:
```
Mon Feb 17 12:49:58 2025       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 550.127.05             Driver Version: 550.127.05     CUDA Version: 12.4     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce GTX 1060 6GB    Off |   00000000:01:00.0 Off |                  N/A |
| 24%   41C    P8             10W /  120W |    4633MiB /   6144MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
                                                                                         
+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI        PID   Type   Process name                              GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A     41879      C   uwsgi                                        2088MiB |
|    0   N/A  N/A     41880      C   uwsgi                                        2542MiB |
+-----------------------------------------------------------------------------------------+
```
6. run `ls -la /dev/nvidia*` on host. The output should look like
```
crw-rw-rw- 1 root root 195,   0 Feb 17 12:26 /dev/nvidia0
crw-rw-rw- 1 root root 195, 255 Feb 17 12:26 /dev/nvidiactl
crw-rw-rw- 1 root root 234,   0 Feb 17 12:26 /dev/nvidia-uvm
crw-rw-rw- 1 root root 234,   1 Feb 17 12:26 /dev/nvidia-uvm-tools

/dev/nvidia-caps:
total 0
drwxr-xr-x  2 root root     80 Feb 17 12:26 .
drwxr-xr-x 20 root root   4680 Feb 17 12:26 ..
cr--------  1 root root 238, 1 Feb 17 12:26 nvidia-cap1
cr--r--r--  1 root root 238, 2 Feb 17 12:26 nvidia-cap2
```
7. edit your LXC config file, e.g. `/etc/pve/lxc/101.conf` and add following lines. Mind the cgroups e.g. `234:*` - those are taken from the output of `ls -la /dev/nvidia*` on host.
```
lxc.cgroup2.devices.allow: c 195:* rwm
lxc.cgroup2.devices.allow: c 234:* rwm
lxc.cgroup2.devices.allow: c 238:* rwm
lxc.mount.entry: /dev/nvidia0 dev/nvidia0 none bind,optional,create=file
lxc.mount.entry: /dev/nvidiactl dev/nvidiactl none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm dev/nvidia-uvm none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-uvm-tools dev/nvidia-uvm-tools none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-caps/nvidia-cap1 dev/nvidia-caps/nvidia-cap1 none bind,optional,create=file
lxc.mount.entry: /dev/nvidia-caps/nvidia-cap2 dev/nvidia-caps/nvidia-cap2 none bind,optional,create=file
```

### LXC setup
1. install guest drivers in LXC. Same as in #1 of host setup, but run with `--no-kernel-module` argument.
2. `nvidia-smi` in LXC should work now.
3. run `docker run --rm -ti --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all ubuntu:22.04 nvidia-smi -l` to verify if it works in docker