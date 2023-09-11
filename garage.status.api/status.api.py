# this runs on home server, remembers the state of garage
from flask import Flask, Response, request
from enum import Enum
from datetime import datetime

class States(str,Enum):
    UNKNOWN = 'UNKNOWN'
    CLOSING = 'CLOSING'
    OPENING = 'OPENING'
    CLOSED = 'CLOSED'
    OPENED = 'OPENED'
states = [member.value for member in States]
UNKNOWN_STATE_GRACE_PERIOD = 180

garage_state = {
    'state' : States.UNKNOWN,
    'last_updated' : datetime.min,
    'last_health' : datetime.utcnow()
}

app = Flask(__name__)

@app.post('/')
def do_POST():
    post_body = request.json
    if post_body['state'] in states:
        garage_state['state'] = post_body['state']
        now = datetime.utcnow()
        garage_state['last_updated'] = now
        garage_state['last_health'] = now
        return Response(status=202)
    else:
        return Response(status=400)

@app.route('/', methods=['HEAD'])
def do_HEAD():
    garage_state['last_health'] = datetime.utcnow()
    return Response(status=200)

@app.route('/', methods=['GET'])
def do_GET():
    now = datetime.utcnow()
    is_past_grace_period = (now - garage_state['last_health']).total_seconds() > UNKNOWN_STATE_GRACE_PERIOD
    is_last_known_state_closed = garage_state['state'] == States.CLOSED
    if (is_past_grace_period and is_last_known_state_closed is False):
        garage_state['state'] = States.UNKNOWN
    return garage_state

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)