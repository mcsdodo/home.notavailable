from flask import Flask, Response
import serial

import configparser
try:
    from garagegpio import GarageGpio
except ImportError:
    from garagegpio_mock import GarageGpio
from time import sleep

CONFIG = configparser.ConfigParser()
CONFIG.read(['config.ini', 'secrets.ini'])
DOOR_CLOSED_SENSOR_PIN = int(CONFIG['common']['DoorSensorClosedPin'])
DOOR_OPENED_SENSOR_PIN = int(CONFIG['common']['DoorSensorOpenedPin'])
RELAY_PIN = int(CONFIG['common']['RelayPin'])
RAMP_PHONE = CONFIG['controller.api']['RampPhone']

gpio = GarageGpio(DOOR_OPENED_SENSOR_PIN, DOOR_CLOSED_SENSOR_PIN, RELAY_PIN)

def getState():
    if gpio.is_door_sensor_closed():
        return 'CLOSED'
    if gpio.is_door_sensor_opened():
        return 'OPENED'
    return { 'state' : 'UNKNOWN'}

app = Flask(__name__)

@app.post('/')
def do_POST():
    gpio.relay_on()
    print("R1 turned on")
    sleep(1)
    gpio.relay_off()
    print("R2 turned off")
    return Response(status=200)

@app.get('/')
def do_GET():
    return {
        'state' : getState()
    }

@app.post('/open-ramp')
def do_openRamp_POST():
    ser = serial.Serial(
        port='/dev/serial0',
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
    )
    ser.write(('ATD'+RAMP_PHONE+';\r').encode())
    ser.write('WAIT=5\r'.encode())
    sleep(10)
    ser.write('ATH\r'.encode())
    ser.close()
    return Response(status=200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)