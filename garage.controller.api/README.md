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
WorkingDirectory=/home/dodo/garage
ExecStart=/usr/bin/python3 /home/dodo/garage/controller.api.py

[Install]
WantedBy=multi-user.target
```
```
sudo nano daemon-reload
sudo nano enable garageserver.service
sudo nano start garageserver.service
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
WorkingDirectory=/home/dodo/garage
ExecStart=/usr/bin/python3 /home/dodo/garage/status.service.py

[Install]
WantedBy=multi-user.target
```
```
sudo nano daemon-reload
sudo nano enable garagestatus.service
sudo nano start garagestatus.service
```


To test relay locally on PiZero
```
wget -qO- http://localhost:8080 --post-data=
```

To test door sensor locally on PiZero
```
wget -qO- http://localhost:8080
```

Don't commit secrets to Github!

```
git update-index --skip-worktree garage.controller.api/config.ini
```
