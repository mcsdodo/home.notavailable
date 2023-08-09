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

gpio = GarageGpio(DOOR_OPENED_SENSOR_PIN, DOOR_CLOSED_SENSOR_PIN)

# state vars
isClosed = gpio.is_door_sensor_closed()

garageTriggerWatch = TriggerTimer(OPENED_SECONDS_WARNING_AFTER)
healthReportWatch = TriggerTimer(HEALTH_REPORTING_INTERVAL)
warningReportWatch = TriggerTimer(OPENED_SECONDS_WARNING_INTERVAL, True)

def log(message):
    print(datetime.utcnow().strftime("%H:%M:%S"), message)

log("Status service started. Reporting door is " + ("CLOSED" if isClosed else "OPENED"))
CLIENT.set_status('CLOSED' if isClosed else 'OPENED')

try:
    while True:
        time.sleep(POLLING_INTERVAL)
        isDoorSensorClosed = gpio.is_door_sensor_closed()
        isDoorSensorOpened = gpio.is_door_sensor_opened()
        now = datetime.utcnow()

        if isDoorSensorClosed is False and isClosed is True:
            log("Door started opening")
            garageTriggerWatch.reset(now)
            isClosed = False
        
        # TBD after sensor is mounted
        # if isDoorSensorOpened is False and isClosed is False:
        #     log("Door started closing")
        #     garageTriggerWatch.reset(now)
        
        if (garageTriggerWatch.hasElapsed()
            and warningReportWatch.hasElapsed()
            and isDoorSensorClosed is False):
            triggerElapsed =  garageTriggerWatch.elapsedSeconds()
            log("Door has been opened for " + str(int(round(triggerElapsed))) + " seconds")
            warningReportWatch.reset(now)
            healthReportWatch.reset(now)
            CLIENT.set_status('OPENED')
            continue

        if (healthReportWatch.hasElapsed()):
            log("Reporting health.")
            CLIENT.report_health()
            healthReportWatch.reset(now)
        
        if isDoorSensorClosed:
            if isClosed is False:
                CLIENT.set_status('CLOSED')
                healthReportWatch.reset(now)
                log("Door was just closed")
            garageTriggerWatch.reset(datetime.max)
            isClosed = True
        
        # TBD after sensor is mounted
        # if isDoorSensorOpened:
        #     if isClosed is True:
        #         CLIENT.set_status('OPENED')
        #         healthReportWatch.reset(now)
        #         log("Door was just opened")
        #     garageTriggerWatch.reset(now)
        #     isClosed = False

except KeyboardInterrupt:
    print("Program exited")
    gpio.cleanup()
