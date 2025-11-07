#!/bin/bash
git pull
sudo systemctl restart garageserver.service
journalctl --unit garageserver.service --since "1 minute ago"
sudo systemctl restart garagestatus.service
journalctl --unit garagestatus.service --since "1 minute ago"