
import RPi.GPIO as GPIO
class GarageGpio:
    def __init__(self, door_opened_sensor_pin = 15, door_closed_sendor_pin = 11, relay_pin = 31):
        self._door_opened_sensor_pin = door_opened_sensor_pin
        self._door_closed_sendor_pin = door_closed_sendor_pin
        self._relay_pin = relay_pin
        # setup pins
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self._door_closed_sendor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self._door_opened_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self._relay_pin, GPIO.OUT, initial=GPIO.LOW)

    def is_door_sensor_closed(self):
        return GPIO.input(self._door_closed_sendor_pin) == 0
    
    def is_door_sensor_opened(self):
        return GPIO.input(self._door_opened_sensor_pin) == 0
    
    def relay_on(self):
        GPIO.output(self._relay_pin, GPIO.HIGH)

    def relay_off(self):
        GPIO.output(self._relay_pin, GPIO.LOW)
    
    def cleanup(self):
        GPIO.cleanup()
