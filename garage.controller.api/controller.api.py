# this runs on the PiZero in garage. Basic garage operation

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import configparser
try:
    from garagegpio import GarageGpio
except ImportError:
    from garagegpio_mock import GarageGpio
from time import sleep

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
DOOR_CLOSED_SENSOR_PIN = int(CONFIG['common']['DoorSensorClosedPin'])
DOOR_OPENED_SENSOR_PIN = int(CONFIG['common']['DoorSensorOpenedPin'])
RELAY_PIN = int(CONFIG['common']['RelayPin'])

gpio = GarageGpio(DOOR_OPENED_SENSOR_PIN, DOOR_CLOSED_SENSOR_PIN, RELAY_PIN)

def getState():
    if gpio.is_door_sensor_closed():
        return 'CLOSED'
    if gpio.is_door_sensor_opened():
        return 'OPENED'
    return { 'state' : 'UNKNOWN'}

class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self, status, message=None):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if message is not None:
            self.wfile.write(json.dumps(message, default=str).encode('utf-8'))
        
    def do_POST(self):
        gpio.relay_on()
        print("R1 turned on")
        sleep(1)
        gpio.relay_off()
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
        gpio.cleanup()

    webServer.server_close()
    print("Server stopped.")