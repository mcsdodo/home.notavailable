# this runs on the PiZero in garage. Basic garage operation

from http.server import BaseHTTPRequestHandler, HTTPServer
import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BOARD)
hostName = "0.0.0.0"
serverPort = 8080

class Relay:
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
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):

        r1 = Relay("R1")
        r1.on()
        print("R1 turned on")
        sleep(1)
        r1.off()
        print("R2 turned off")

        self._set_headers()
        self.wfile.write(bytes("OK", "utf-8"))
    
    def do_HEAD(self):
        self._set_headers()

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