# this runs on the PiZero in garage. Endless loop with state checking and reporting back to home server.

import time
from datetime import datetime
import RPi.GPIO as GPIO
import configparser
from statusapiclient import StatusApiClient

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
CLIENT = StatusApiClient(CONFIG['status.api'])

POLLING_INTERVAL = float(CONFIG['status.service']['PollingInterval'])
OPENED_SECONDS_WARNING_AFTER = int(CONFIG['status.service']['OpenedSecondsWarningAfter'])
OPENED_SECONDS_WARNING_INTERVAL = int(CONFIG['status.service']['OpenedSecondsWarningInterval'])
HEALTH_REPORTING_INTERVAL = int(CONFIG['status.service']['HealthReportingInterval'])
IS_CLOSED = False
DOOR_SENSOR_PIN = 11

# setup pins
GPIO.setmode(GPIO.BOARD)
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

garageTriggerTime = datetime.utcnow()
healthReportTime = datetime.utcnow()
warningReportTime = datetime.utcnow()

class PrinterWithTimestamp:
    def print(self, message):
        print(datetime.utcnow().strftime("%H:%M:%S"), message)

p = PrinterWithTimestamp()

p.print("Status service started")

try:
    while True:
        time.sleep(POLLING_INTERVAL)
        isDoorSensorClosed = GPIO.input(DOOR_SENSOR_PIN) == 0
        now = datetime.utcnow()
        lastTriggerDiff = (now - garageTriggerTime).total_seconds()
        lastHealthReportDiff = (now - healthReportTime).total_seconds()
        warningReportDiff = (now - warningReportTime).total_seconds()

        if isDoorSensorClosed is False and IS_CLOSED is True:
            p.print("Door started opening")
            CLIENT.set_status('OPENING')
            garageTriggerTime = now
            healthReportTime = now
            IS_CLOSED = False
            continue
        
        if (lastTriggerDiff > OPENED_SECONDS_WARNING_AFTER 
            and warningReportDiff > OPENED_SECONDS_WARNING_INTERVAL
            and isDoorSensorClosed is False):
            p.print("Door has been opened for " + str(int(round(lastTriggerDiff))) + " seconds")
            CLIENT.set_status('OPENED')
            warningReportTime = now
            healthReportTime = now
            continue

        if (lastHealthReportDiff > HEALTH_REPORTING_INTERVAL):
            p.print("Reporting health.")
            healthReportTime = now
            CLIENT.report_health()

        if isDoorSensorClosed:
            if IS_CLOSED is False:
                CLIENT.set_status('CLOSED')
                healthReportTime = now
                p.print("Door was just closed")
            garageTriggerTime = datetime.max
            IS_CLOSED = True


except KeyboardInterrupt:
    print("Program exited")
    GPIO.cleanup()
