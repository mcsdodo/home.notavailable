import time
from datetime import datetime
from periodwatch import TriggerTimer

print("DELAYED")

watch = TriggerTimer(1, False)

def log(message):
    print(datetime.utcnow().strftime("%H:%M:%S.%f"), message)

fn = lambda : log("executing")
w_fn = lambda: log("waiting")

watch.executeIfElapsed(fn, w_fn)

time.sleep(1)

watch.executeIfElapsed(fn, w_fn)
watch.executeIfElapsed(fn, w_fn)

time.sleep(1)
watch.executeIfElapsed(fn, w_fn)

print("")
print("IMMEDIATELY")

watch = TriggerTimer(1, True)
watch.executeIfElapsed(fn, w_fn)
watch.executeIfElapsed(fn, w_fn)

time.sleep(1)
watch.executeIfElapsed(fn, w_fn)