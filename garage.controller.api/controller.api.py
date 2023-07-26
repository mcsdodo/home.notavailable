# this runs on the PiZero in garage. Basic garage operation

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import configparser
import RPi.GPIO as GPIO
from time import sleep

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
DOOR_SENSOR_PIN = int(CONFIG['common']['DoorSensorPin'])

GPIO.setmode(GPIO.BOARD)
hostName = "0.0.0.0"
serverPort = 8080

class SBCRelay:
    relay_pins = {"R1":31,"R2":33,"R3":35,"R4":37}

    def __init__(self, pins):
        self.pin = self.relay_pins[pins]
        self.pins = pins
        GPIO.setup(self.pin,GPIO.OUT,initial=GPIO.LOW)

    def on(self):
        GPIO.output(self.pin,GPIO.HIGH)

    def off(self):
        GPIO.output(self.pin,GPIO.LOW)

class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self, status, message=None):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if message is not None:
            self.wfile.write(json.dumps(message, default=str).encode('utf-8'))

    def do_POST(self):
        r_1 = SBCRelay("R1")
        r_1.on()
        print("R1 turned on")
        sleep(1)
        r_1.off()
        print("R2 turned off")
        self._set_headers(200)
    
    def do_GET(self):
        state = 'CLOSED' if (GPIO.input(DOOR_SENSOR_PIN) == 0) else 'OPENED'
        self._set_headers(200, { 'state' : state })

    def do_HEAD(self):
        self._set_headers(200)
    
if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()

    webServer.server_close()
    print("Server stopped.")