To install controller API on PiZero
```
sudo nano /etc/systemd/system/garageserver.service
```

```sh
[Unit]
Description=Garage opener python http service
After=multi-user.target

[Service]
Type=idle
User=dodo
WorkingDirectory=/home/dodo/home.notavailable/garage.controller.api
ExecStart=/usr/bin/python3 /home/dodo/home.notavailable/garage.controller.api/controller.api.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
```
sudo systemctl daemon-reload
sudo systemctl enable garageserver.service
sudo systemctl start garageserver.service
sudo systemctl status garageserver.service
```

To install updater API on PiZero
```
sudo nano /etc/systemd/system/garageupdater.service
```

```sh
[Unit]
Description=Garage garageupdater python http service
After=multi-user.target

[Service]
Type=idle
User=dodo
WorkingDirectory=/home/dodo/home.notavailable/garage.controller.api
ExecStart=/usr/bin/python3 /home/dodo/home.notavailable/garage.controller.api/updater.api.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
```
sudo systemctl daemon-reload
sudo systemctl enable garageupdater.service
sudo systemctl start garageupdater.service
sudo systemctl status garageupdater.service
```


To install status service on PiZero
```
sudo nano /etc/systemd/system/garagestatus.service
```

```sh
[Unit]
Description=Garage status reporting service
After=multi-user.target

[Service]
Type=idle
User=dodo
WorkingDirectory=/home/dodo/home.notavailable/garage.controller.api
ExecStart=/usr/bin/python3 /home/dodo/home.notavailable/garage.controller.api/status.service.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
```
sudo systemctl daemon-reload
sudo systemctl enable garagestatus.service
sudo systemctl start garagestatus.service
sudo systemctl status garagestatus.service
```


To test relay locally on PiZero
```
wget -qO- http://localhost:8080 --post-data=
```

To test door sensor locally on PiZero
```
wget -qO- http://localhost:8080
```


To update
```
wget -qO- http://localhost:8081/update --post-data=
```



git config --list --show-origin --show-scope
git config --global --add safe.directory /home/dodo/home.notavailable


## Tailscale networking

a LXC runnig tailscale needs to have following mount:
``lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file``

Run ``sudo tailscale up --accept-routes --advertise-routes=192.168.0.0/24`` on PiZero.


Caddy chain:
1. 192.168.0.2 - LXC
2. 192.168.0.113 - Proxmox1 (small)
3. 192.168.0.213 - Proxmox2 (media)
4. 192.168.0.214 - Proxmox3 (ai)

### Main all proxmox servers
``tailscale up --accept-dns=false --reset``

### Small server

Run ``sudo tailscale up --advertise-routes=192.168.0.2/32,192.168.0.121/32,192.168.0.204/32,192.168.0.112/32,192.168.0.113/32,192.168.0.10/32,192.168.0.11/32,192.168.0.12/32,192.168.0.13/32,192.168.0.14/32 --accept-routes --accept-dns=false`` on local infrastructure.

### Big server
```sudo tailscale up --advertise-routes=192.168.0.115/32,192.168.0.208/32,192.168.0.122/32,192.168.0.212/32,192.168.0.201/32,192.168.0.213/32,192.168.0.214/32,,192.168.0.235/32 --accept-routes --accept-dns=false```

Home assistant runs https://github.com/lmagyar/homeassistant-addon-tailscale addon.


