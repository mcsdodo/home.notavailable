from datetime import datetime

class TriggerTimer:
    def __init__(self, interval, start_immediately = False):
        self._interval = interval
        self._init_time = datetime.min if start_immediately else datetime.utcnow()

    def elapsedSeconds(self):
        now = datetime.utcnow()
        diff = (now - self._init_time).total_seconds()
        return diff

    def hasElapsed(self):
        return self.elapsedSeconds() > self._interval
    
    def reset(self, time):
        self._init_time = time
    
    def executeIfElapsed(self, function, waiting_fn = lambda: ()):
        if (self.hasElapsed()):
            function()
            self.reset(datetime.utcnow())
        else:
            waiting_fn()
        