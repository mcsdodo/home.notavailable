# Portainer docker run
With automated reverse proxy configuration for Caddy.
```
docker run --network=caddy -l caddy=http://portainer.lan -l caddy.reverse_proxy="{{upstreams 9000}}" \
-d -p 9000:9000 --name portainer --restart=always \
-v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:latest --trusted-origins=portainer.lan
```

# Proxmox mounts
``nano /etc/fstab``

192.168.0.101:/mnt/HD/HD_a2/Photos /mnt/pve/NotAvailableCldPhotos nfs nfsvers=3 0 0
192.168.0.101:/mnt/HD/HD_a2/Public /mnt/pve/NotAvailableCldPublic nfs nfsvers=3 0 0

# To run portainer on multiple LXCs and manage from one install portainer-agent
```
docker run -d \
  -p 9001:9001 \
  --name portainer_agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:2.27.9
```

## NUT

https://docs.deeztek.com/books/ubuntu/page/installing-nut-network-ups-tools-on-ubuntu-1804-lts


```
apt-get update​
apt-get upgrade​
apt install nut -y​
```

chgrp -R nut /etc/nut /dev/bus/usb
chmod -R o-rwx /etc/nut

sudo usermod -a -G root nut


``nano /etc/nut/ups.conf``
```
pollinterval=15
maxretry  = 3

[ups]
  driver=nutdrv_qx
  port=auto
#  vendorid=0665
#  productid=5161
#  serial=D00F06103A84
  desc="UPS"
```


cat >/etc/udev/rules.d/99-usb-serial.rules <<EOF
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="0665", ATTRS{idProduct}=="5161", MODE="0660", GROUP="nut"
EOF
udevadm control --reload-rules && udevadm trigger


nut-scanner

[nutdev1]
        driver = "nutdrv_qx"
        port = "auto"
        vendorid = "0665"
        productid = "5161"
        bus = "001"
        device = "043"
        busport = "007"
        ###NOTMATCHED-YET###bcdDevice = "0003"



systemctl status nut-server


upsd

upsdrvctl start

upsc ups@localhost