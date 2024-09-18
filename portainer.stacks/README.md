# Portainer docker run

docker run -d -p 9000:9000 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:latest

# Proxmox mounts
``nano /etc/fstab``

192.168.100.101:/mnt/HD/HD_a2/Photos /mnt/pve/NotAvailableCldPhotos nfs nfsvers=3 0 0
192.168.100.101:/mnt/HD/HD_a2/Public /mnt/pve/NotAvailableCldPublic nfs nfsvers=3 0 0

# LXC MPs

## 101 - alpine-docker@proxmox
nano /etc/pve/lxc/101.conf

mp0: /mnt/pve/NotAvailableCldPhotos,mp=/mnt/photos
mp1: /mnt/pve/NotAvailableCldPublic/Media/Downloads,mp=/mnt/downloads


## 118 - alpine-docker@proxmox2
nano /etc/pve/lxc/118.conf

mp0: /mnt/pve/media,mp=/mnt/media
mp1: /mnt/pve/immich,mp=/mnt/immich
mp2: /mnt/pve/NotAvailableCloudPublic/Media/,mp=/mnt/oldmedia

# Trust caddy cert
caddy_windows_amd64.exe trust --address 192.168.100.2:2019


# To run portainer on multiple LXCs and manage from one install portainer-agent
```
docker run -d \
  -p 9001:9001 \
  --name portainer_agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:2.19.5
```