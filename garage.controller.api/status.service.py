# this runs on the PiZero in garage. Endless loop with state checking and reporting back to home server.

import time
from datetime import datetime
try:
    from garagegpio import GarageGpio
except ImportError:
    from garagegpio_mock import GarageGpio
import configparser
from statusapiclient import StatusApiClient

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
garageTriggerTime = datetime.utcnow()
healthReportTime = datetime.utcnow()
warningReportTime = datetime.min

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
        lastGarageTriggerDiff = (now - garageTriggerTime).total_seconds()
        lastHealthReportDiff = (now - healthReportTime).total_seconds()
        lastWarningReportDiff = (now - warningReportTime).total_seconds()

        if isDoorSensorClosed is False and isClosed is True:
            log("Door started opening")
            garageTriggerTime = now
            isClosed = False
        
        # TBD after sensor is mounted
        # if isDoorSensorOpened is False and isClosed is False:
        #     log("Door started closing")
        #     garageTriggerTime = now
        
        if (lastGarageTriggerDiff > OPENED_SECONDS_WARNING_AFTER
            and lastWarningReportDiff > OPENED_SECONDS_WARNING_INTERVAL
            and isDoorSensorClosed is False):
            log("Door has been opened for " + str(int(round(lastGarageTriggerDiff))) + " seconds")
            warningReportTime = now
            healthReportTime = now
            if (lastGarageTriggerDiff < OPENED_SECONDS_WARNING_INTERVAL + 10):
                CLIENT.set_status('OPENED')
                continue

        if (lastHealthReportDiff > HEALTH_REPORTING_INTERVAL):
            log("Reporting health.")
            healthReportTime = now
            CLIENT.report_health()

        if isDoorSensorClosed:
            if isClosed is False:
                CLIENT.set_status('CLOSED')
                healthReportTime = now
                log("Door was just closed")
            garageTriggerTime = datetime.max
            isClosed = True
        
        # TBD after sensor is mounted
        # if isDoorSensorOpened:
        #     if isClosed is True:
        #         CLIENT.set_status('OPENED')
        #         healthReportTime = now
        #         log("Door was just opened")
        #     garageTriggerTime = now
        #     isClosed = False

except KeyboardInterrupt:
    print("Program exited")
    gpio.cleanup()
