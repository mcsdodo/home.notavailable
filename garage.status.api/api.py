from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from enum import Enum
from datetime import datetime

class States(str,Enum):
    UNKNOWN = 'UNKNOWN'
    CLOSED = 'CLOSED'
    OPENING = 'OPENING'
    OPENED = 'OPENED'
    ACTIVATED = 'ACTIVATED'
states = [member.value for member in States]

garage_state = {
    'state' : States.UNKNOWN,
    'last_updated' : datetime.min
}

class Api(BaseHTTPRequestHandler):
    
    def _response(self, status, message=None):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if message != None:
            self.wfile.write(json.dumps(message, default=str).encode('utf-8'))

    def do_GET(self):
        self._response(200, garage_state)
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_body = json.loads(self.rfile.read(content_length))
        if post_body['state'] in states:
            garage_state['state'] = post_body['state']
            garage_state['last_updated'] = datetime.now()
            self._response(202)
        else:
            self._response(400)

if __name__ == "__main__":
    HOST_NAME = "0.0.0.0"
    SERVER_PORT = 8080
    webServer = HTTPServer((HOST_NAME, SERVER_PORT), Api)
    print("Server started http://%s:%s" % (HOST_NAME, SERVER_PORT))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    print("Server stopped.")