Install docker loki plugin:

```
docker plugin install grafana/loki-docker-driver:2.9.2 --alias loki --grant-all-permissions
```

```
    logging:
      driver: loki
      options:
        loki-url: http://loki.local/loki/api/v1/push
```        