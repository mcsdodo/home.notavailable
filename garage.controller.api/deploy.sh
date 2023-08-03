#!/bin/bash
git pull
sudo systemctl restart garageserver.service
sudo systemctl restart garagestatus.service
journalctl --unit garageserver.service -n 20