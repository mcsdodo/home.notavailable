# xcaddy with TCP layer4 for MQTT proxy

I'm using layer4 to proxy mqtt traffic to my mqtt broker. Following configuration seems to work (except for esp32 devices - they seem to have hard time connecting with FQDN, connecting with IP - even proxied - works file):

```
{
    admin :2019 {
		origins 192.168.0.2, 0.0.0.0, localhost
	}
    layer4 {
		mqtt.lan:8883 {
			route {
				proxy {
					upstream 192.168.0.204:8883
				}
			}
		}
		mqtt.lan:1883 {
			route {
				proxy {
					upstream 192.168.0.204:1883
				}
			}
		}
	}
}
```

## /etc/resolv.conf
search local
nameserver 192.168.0.121
nameserver 192.168.0.122

## Install Go
```shell
wget https://go.dev/dl/go1.23.1.linux-amd64.tar.gz #for RPI build use https://go.dev/dl/go1.23.1.linux-armv6l.tar.gz

tar -C /usr/local -xzf go1.23.1.linux-amd64.tar.gz

rm go1.23.1.linux-amd64.tar.gz

export PATH=$PATH:/usr/local/go/bin

go version
```

## Build xcaddy with caddy-l4
```shell
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/xcaddy/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-xcaddy-archive-keyring.gpg

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/xcaddy/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-xcaddy.list

sudo apt update

sudo apt install xcaddy

xcaddy build --with github.com/mholt/caddy-l4
```

## Create Caddyfile
```shell
nano Caddyfile
```

```shell
./caddy run --config Caddyfile
```

## Create caddy.service
```shell
cat > /etc/systemd/system/caddy.service << EOF
[Unit]
Description=Caddy
Documentation=https://caddyserver.com/docs/
After=network.target network-online.target
Requires=network-online.target

[Service]
Type=notify
ExecStart=/root/caddy run --environ --config /root/Caddyfile
ExecReload=/root/caddy reload --config /root/Caddyfile --force
TimeoutStopSec=5s
LimitNOFILE=1048576
PrivateTmp=true
ProtectSystem=full
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF
```

## Trust caddy cert
`caddy_windows_amd64.exe trust --address 192.168.0.2:2019`

## Test mqtt

`mosquitto_sub -h mqtt.lan -t espresense/# -u **** -P ****`