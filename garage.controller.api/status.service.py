# this runs on the PiZero in garage. Endless loop with state checking and reporting back to home server.

import time
from datetime import datetime
try:
    from garagegpio import GarageGpio
except ImportError:
    from garagegpio_mock import GarageGpio
import configparser
from statusapiclient import StatusApiClient
from triggertimer import TriggerTimer

CONFIG = configparser.ConfigParser()
CONFIG.read(['config.ini', 'secrets.ini'])
CLIENT = StatusApiClient(CONFIG['status.api'])

POLLING_INTERVAL = float(CONFIG['status.service']['PollingInterval'])
OPENED_SECONDS_WARNING_AFTER = int(CONFIG['status.service']['OpenedSecondsWarningAfter'])
OPENED_SECONDS_WARNING_INTERVAL = int(CONFIG['status.service']['OpenedSecondsWarningInterval'])
HEALTH_REPORTING_INTERVAL = int(CONFIG['status.service']['HealthReportingInterval'])
DOOR_CLOSED_SENSOR_PIN = int(CONFIG['common']['DoorSensorClosedPin'])
DOOR_OPENED_SENSOR_PIN = int(CONFIG['common']['DoorSensorOpenedPin'])
FAST_FEEDBACK = int(CONFIG['status.service']['FastFeedback'])

gpio = GarageGpio(DOOR_OPENED_SENSOR_PIN, DOOR_CLOSED_SENSOR_PIN)

# state vars
isClosed = gpio.is_door_sensor_closed()
isOpened = gpio.is_door_sensor_opened()

garageTriggerWatch = TriggerTimer(OPENED_SECONDS_WARNING_AFTER)
healthReportWatch = TriggerTimer(HEALTH_REPORTING_INTERVAL)
warningReportWatch = TriggerTimer(OPENED_SECONDS_WARNING_INTERVAL, True)

def log(message):
    print(datetime.utcnow().strftime("%H:%M:%S"), message)

state = ("CLOSED" if isClosed else ("OPENED" if isOpened else "UNKNOWN"))
log("Status service started. Reporting door is " + state)
CLIENT.set_status(state)

try:
    while True:
        time.sleep(POLLING_INTERVAL)
        isDoorSensorClosed = gpio.is_door_sensor_closed()
        isDoorSensorOpened = gpio.is_door_sensor_opened()
        now = datetime.utcnow()

        if isDoorSensorClosed is False and isClosed is True and isOpened is False:
            log("Door started opening")
            garageTriggerWatch.reset(now)
            isClosed = False
            if (FAST_FEEDBACK == 1):
                CLIENT.set_status('OPENING')
        
        if isDoorSensorOpened is False and isClosed is False and isOpened is True:
            log("Door started closing")
            garageTriggerWatch.reset(now)
            isOpened = False
            if (FAST_FEEDBACK == 1):
                CLIENT.set_status('CLOSING')
        
        if (garageTriggerWatch.hasElapsed()
            and warningReportWatch.hasElapsed()
            and isDoorSensorClosed is False):
            triggerElapsed =  garageTriggerWatch.elapsedSeconds()
            
            warningReportWatch.reset(now)
            healthReportWatch.reset(now)
            state = 'OPENED' if isDoorSensorOpened else 'UNKNOWN'
            CLIENT.set_status(state)
            log("Door has been " + state + " for " + str(int(round(triggerElapsed))) + " seconds")
            continue

        if (healthReportWatch.hasElapsed()):
            log("Reporting health.")
            if (isDoorSensorClosed):
                CLIENT.report_health("/0")
            elif (isDoorSensorOpened):
                CLIENT.report_health("/1")
            else:
                CLIENT.report_health()
            healthReportWatch.reset(now)
        
        if isDoorSensorClosed:
            if isClosed is False:
                CLIENT.set_status('CLOSED')
                healthReportWatch.reset(now)
                log("Door was just closed")
            garageTriggerWatch.reset(datetime.max)
            isClosed = True
        
        if isDoorSensorOpened:
            if isOpened is False:
                CLIENT.set_status('OPENED')
                healthReportWatch.reset(now)
                log("Door was just opened")
                garageTriggerWatch.reset(now)
            isOpened = True

except KeyboardInterrupt:
    print("Program exited")
    gpio.cleanup()
