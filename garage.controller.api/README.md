``sudo nano /etc/systemd/system/garageserver.service``

```sh
[Unit]
Description=Garage opener python http service
After=multi-user.target

[Service]
Type=idle
WorkingDirectory=/home/dodo/garage
ExecStart=/usr/bin/python3 /home/dodo/garage/controller.api.py

[Install]
WantedBy=multi-user.target
```

``sudo nano /etc/systemd/system/garagestatus.service``

```sh
[Unit]
Description=Garage status reporting service
After=multi-user.target

[Service]
Type=idle
WorkingDirectory=/home/dodo/garage
ExecStart=/usr/bin/python3 /home/dodo/garage/status.service.py

[Install]
WantedBy=multi-user.target
```

```
wget -qO- http://localhost:8080 --post-data=
```

```
wget -qO- http://localhost:8080
```