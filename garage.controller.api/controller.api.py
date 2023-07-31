# this runs on the PiZero in garage. Basic garage operation

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import configparser
import RPi.GPIO as GPIO
from time import sleep
import subprocess

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
DOOR_CLOSED_SENSOR_PIN = int(CONFIG['common']['DoorSensorClosedPin'])
DOOR_OPENED_SENSOR_PIN = int(CONFIG['common']['DoorSensorOpenedPin'])
RELAY_PIN = int(CONFIG['common']['RelayPin'])

GPIO.setmode(GPIO.BOARD)
GPIO.setup(DOOR_CLOSED_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DOOR_OPENED_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def getState():
    if GPIO.input(DOOR_CLOSED_SENSOR_PIN) == 0:
        return 'CLOSED'
    if GPIO.input(DOOR_OPENED_SENSOR_PIN) == 0:
        return 'OPENED'
    return { 'state' : 'UNKNOWN'}

class Relay:
    def __init__(self):
        GPIO.setup(RELAY_PIN,GPIO.OUT,initial=GPIO.LOW)

    def on(self):
        GPIO.output(RELAY_PIN,GPIO.HIGH)

    def off(self):
        GPIO.output(RELAY_PIN,GPIO.LOW)

class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self, status, message=None):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if message is not None:
            self.wfile.write(json.dumps(message, default=str).encode('utf-8'))
        
    def do_POST(self):
        if self.path == '/update':
            output = subprocess.run(["/usr/bin/bash", "/home/dodo/home.notavailable/garage.controller.api/deploy.sh"], cwd='/home/dodo/home.notavailable/', capture_output=True, text=True)
            if (output.returncode == 0):
                self._set_headers(200, output.stdout.encode())
            else:
                self._set_headers(500, output.stderr.encode())
        else:
            r_1 = Relay()
            r_1.on()
            print("R1 turned on")
            sleep(1)
            r_1.off()
            print("R2 turned off")
            self._set_headers(200)
    
    def do_GET(self):
        self._set_headers(200, { 'state' : getState() })

    def do_HEAD(self):
        self._set_headers(200)
    
if __name__ == "__main__":
    HOST_NAME = "0.0.0.0"
    SERVER_PORT = 8080
    webServer = HTTPServer((HOST_NAME, SERVER_PORT), MyServer)
    print("Server started http://%s:%s" % (HOST_NAME, SERVER_PORT))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()

    webServer.server_close()
    print("Server stopped.")