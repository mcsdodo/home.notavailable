
import RPi.GPIO as GPIO
class GarageGpio:
    def __init__(self, door_opened_sensor_pin, door_closed_sendor_pin):
        self._door_opened_sensor_pin = door_opened_sensor_pin
        self._door_closed_sendor_pin = door_closed_sendor_pin
        # setup pins
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self._door_closed_sendor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self._door_opened_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def is_door_sensor_closed(self):
        return GPIO.input(self._door_closed_sendor_pin) == 0
    
    def is_door_sensor_opened(self):
        return GPIO.input(self._door_opened_sensor_pin) == 0
    
    def cleanup(self):
        GPIO.cleanup()