In this project I'm using this GPRS hat https://www.waveshare.com/wiki/GSM/GPRS/GNSS_HAT

Prerequisite setup:

``sudo raspi-config  -> Interface Options -> Serial Port -> "No" -> "Yes"``

Connect hat, test if works:
```
sudo apt-get update
sudo apt-get install ppp screen
sudo screen /dev/serial0 115200
```

Don't freak out - you should see a completely blank window with a cursor at the top. Type in the letters "AT", capitalized and everything, and hit enter. You should see an "OK" appear - that's the Fona talking back to you! You've verified that the serial connection is working and can exit with Ctrl-A and typing :quit.

``sudo -i``

``wget --no-check-certificate https://raw.githubusercontent.com/mcsdodo/home.notavailable/main/gprs.hat.setup/hat -O /etc/ppp/peers/hat``

``wget --no-check-certificate https://raw.githubusercontent.com/mcsdodo/home.notavailable/main/gprs.hat.setup/hat -O /etc/chatscripts/gprs``

Test hat peer, manually turn on ppp.
``sudo pon hat``
After a while ppp should be on and ``ifconfig`` shoudl list ppp0 with assigned IP address.

Manually turn off with ``sudo poff hat``

```
wget --no-check-certificate https://raw.githubusercontent.com/mcsdodo/home.notavailable/main/gprs.hat.setup/toggle_hat_pwr.sh -O /usr/local/bin/toggle_hat_pwr.sh

chmod 777 /usr/local/bin/toggle_hat_pwr.sh
```

To power on hat on boot:
```
wget --no-check-certificate https://raw.githubusercontent.com/mcsdodo/home.notavailable/main/gprs.hat.setup/hat-poweron.service -O /etc/systemd/system/hat-poweron.service

sudo systemctl enable hat-poweron.service
```

To power off on shutdown:
```
wget --no-check-certificate https://raw.githubusercontent.com/mcsdodo/home.notavailable/main/gprs.hat.setup/hat-poweroff.service -O /etc/systemd/system/hat-poweroff.service

sudo systemctl enable hat-poweroff.service
```

To automatically turn on ppp iface add this
```
auto hat
iface hat inet ppp
   provider hat
```
here ``sudo nano /etc/network/interfaces``


Sources:

https://raw.githubusercontent.com/adafruit/FONA_PPP/master/fona

https://www.waveshare.com/w/upload/4/4a/GSM_GPRS_GNSS_HAT_User_Manual_EN.pdf

https://forums.raspberrypi.com/viewtopic.php?p=1368015&sid=6efe3de74acd33b8e92d7a251e0805c9#p1368015

https://www.digikey.com/en/maker/projects/d0cf660bfc144842a49bfbc5c1dc2ff0

https://learn.adafruit.com/fona-tethering-to-raspberry-pi-or-beaglebone-black/setup

https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=764002


Manual AT commands (using https://github.com/Civlo85/gsmHat)
```
from gsmHat import GSMHat
from time import sleep

gsm = GSMHat('/dev/serial0', 115200)
sleep(2)

Number = 'YOUR_NUMBER'
gsm.Call(Number, 2)

sleep(1)
#gsm.HangUp()
```