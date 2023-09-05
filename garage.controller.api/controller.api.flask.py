from flask import Flask, Response
from gsmHat import GSMHat

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

@app.head('/')
def do_HEAD():
    return Response(status=200)

@app.post('/open-ramp')
def do_openRamp_POST():
    gsm = GSMHat('/dev/serial0', 115200)
    sleep(2)
    gsm.Call(RAMP_PHONE, 2)
    sleep(1)
    gsm.HangUp()
    return Response(status=200)