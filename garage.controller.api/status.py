import time
from datetime import datetime
import RPi.GPIO as GPIO

POLLING_INTERVAL = 0.1
OPENED_SECONDS_WARNING = 5
OPENED_SECONDS_WARNING_INTERVAL = 2
IS_CLOSED = False
DOOR_SENSOR_PIN = 11
RELAY_PIN = 31

# setup pins
GPIO.setmode(GPIO.BOARD)
GPIO.setup(DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

openingTriggerTime = datetime.max

class PiWarning:
    def __init__(self, warning_interval):
        self._warning_interval = warning_interval
        self.last_warning_time = datetime.max

    def warn(self, message):
        last_warning_diff = (datetime.utcnow() - self.last_warning_time).total_seconds()
        if (last_warning_diff > self._warning_interval or last_warning_diff < 0):
            self.print(message)
            self.last_warning_time = datetime.utcnow()

    def print(self, message):
        print(datetime.utcnow().strftime("%H:%M:%S"), message)

opened_warning = PiWarning(OPENED_SECONDS_WARNING_INTERVAL)
activated_warning = PiWarning(OPENED_SECONDS_WARNING_INTERVAL)

try:
    while True:
        isDoorSensorClosed = GPIO.input(DOOR_SENSOR_PIN) is False
        now = datetime.utcnow()
        lastTriggerDiff = (now - openingTriggerTime).total_seconds()

        if isDoorSensorClosed:
            if IS_CLOSED is False:
                opened_warning.print("Door was just closed")
            openingTriggerTime = datetime.max
            IS_CLOSED = True

        if isDoorSensorClosed is False and IS_CLOSED is True:
            opened_warning.print("Door started opening")
            openingTriggerTime = now
            IS_CLOSED = False

        # na "nieco sa deje s dverami" pouzit toto alebo to predtym?
        if GPIO.input(RELAY_PIN):
            activated_warning.warn("Door was activated")
            openingTriggerTime = now
            IS_CLOSED = False

        if lastTriggerDiff > OPENED_SECONDS_WARNING and isDoorSensorClosed is False:
            message = "Door has been opened for " + str(int(round(lastTriggerDiff))) + " seconds"
            opened_warning.warn(message)

        time.sleep(POLLING_INTERVAL)

except KeyboardInterrupt:
    print("Program exited")
    GPIO.cleanup()

# https://raspi.tv/2013/rpi-gpio-basics-7-rpi-gpio-cheat-sheet-and-pointers-to-rpi-gpio-advanced-tutorials#top