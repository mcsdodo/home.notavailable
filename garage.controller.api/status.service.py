# this runs on the PiZero in garage. Endless loop with state checking and reporting back to home server.

import time
from datetime import datetime
import RPi.GPIO as GPIO
import configparser
from statusapiclient import StatusApiClient

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
CLIENT = StatusApiClient(CONFIG['status.api'])

POLLING_INTERVAL = int(CONFIG['status.service']['PollingInterval'])
OPENED_SECONDS_WARNING = int(CONFIG['status.service']['OpenedSecondsWarning'])
OPENED_SECONDS_WARNING_INTERVAL = int(CONFIG['status.service']['OpenedSecondsWarningInterval'])
HEALTH_REPORTING_INTERVAL = int(CONFIG['status.service']['HealthReportingInterval'])
IS_CLOSED = False
DOOR_SENSOR_PIN = 11

# setup pins
GPIO.setmode(GPIO.BOARD)
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

garageTriggerTime = datetime.max
healthReportTime = datetime.max

class PiWarning:
    def __init__(self, warning_interval):
        self._warning_interval = warning_interval
        self.last_warning_time = datetime.max

    def print_with_debounce(self, message):
        last_warning_diff = (datetime.utcnow() - self.last_warning_time).total_seconds()
        if (last_warning_diff > self._warning_interval or last_warning_diff < 0):
            self.print(message)
            self.last_warning_time = datetime.utcnow()

    def print(self, message):
        print(datetime.utcnow().strftime("%H:%M:%S"), message)

warning = PiWarning(OPENED_SECONDS_WARNING_INTERVAL)

try:
    while True:
        time.sleep(POLLING_INTERVAL)
        isDoorSensorClosed = GPIO.input(DOOR_SENSOR_PIN) == 0
        now = datetime.utcnow()
        lastTriggerDiff = (now - garageTriggerTime).total_seconds()
        lastHealthReportDiff = (now - healthReportTime).total_seconds()

        if isDoorSensorClosed:
            if IS_CLOSED is False:
                CLIENT.set_status('CLOSED')
                warning.print("Door was just closed")
            garageTriggerTime = datetime.max
            IS_CLOSED = True
            continue

        if isDoorSensorClosed is False and IS_CLOSED is True:
            warning.print("Door started opening")
            CLIENT.set_status('OPENING')
            garageTriggerTime = now
            IS_CLOSED = False
            continue
        
        if lastTriggerDiff > OPENED_SECONDS_WARNING and isDoorSensorClosed is False:
            warning.print_with_debounce("Door has been opened for " + str(int(round(lastTriggerDiff))) + " seconds")
            CLIENT.set_status('OPENED')
        
        if (lastHealthReportDiff > HEALTH_REPORTING_INTERVAL):
            CLIENT.report_health()

except KeyboardInterrupt:
    print("Program exited")
    GPIO.cleanup()
