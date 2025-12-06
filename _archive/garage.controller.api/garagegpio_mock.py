
file = 'garagestatus.tmp'
class GarageGpio:
    def __init__(self, _, __, ___) -> None:
        pass
    def is_door_sensor_closed(self):
        return self._get_closed()
    
    def is_door_sensor_opened(self):
        return self._get_opened()
    
    def cleanup(self):
        pass

    def _get_closed(self):
        f = open(file, 'r')
        lines = f.readlines()
        val = bool(int(lines[0].strip()))
        return bool(val)
    
    def _get_opened(self):
        f = open(file, 'r')
        lines = f.readlines()
        val = bool(int(lines[1].strip()))
        return val
    
    def relay_on(self):
        pass
    
    def relay_off(self):
        pass