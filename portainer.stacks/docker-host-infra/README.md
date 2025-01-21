# Containers

## Alloy
OTel collector

https://grafana.com/docs/alloy/latest/

## Watchtower
With watchtower you can update the running version of your containerized app simply by pushing a new image to the Docker Hub or your own image registry.

Watchtower will pull down your new image, gracefully shut down your existing container and restart it with the same options that were used when it was deployed initially. Run the watchtower container with the following command:

https://github.com/containrrr/watchtower

Setup notifications: https://github.com/Pyenb/Watchtower-telegram-notifications

## Dockerproxy
This is a security-enhanced proxy for the Docker Socket. In this setup we have one instance of uptime-kuma that needs to monitor multiple docker hosts. It uses dockerproxy to connect to the docker socket of the remote hosts. 

https://github.com/Tecnativa/docker-socket-proxy

## mqdockerup
MqDockerUp is a tool that allows you to monitor and update your docker containers using MQTT and homeassistant.

https://github.com/MichelFR/MqDockerUp

### Required Environment Variables
`MQDOCKERUP_MQTT_TOPIC` has to be set differently for every docker host.