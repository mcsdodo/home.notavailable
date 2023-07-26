``sudo nano /etc/systemd/system/garageserver.service``

```sh
[Unit]
Description=Garage opener python http service
After=multi-user.target

[Service]
Type=idle
ExecStart=/usr/bin/python3 /home/dodo/garage/controller.api.py

[Install]
WantedBy=multi-user.target
```

``sudo nano daemon-reload``
``sudo nano enable garageserver.service``