from http.server import BaseHTTPRequestHandler, HTTPServer
import json

hostName = "0.0.0.0"
serverPort = 8080
garage_state = {
    'state' : -1
}

class Api(BaseHTTPRequestHandler):
    
    def _response(self, status, message=None):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if message != None:
            self.wfile.write(json.dumps(message).encode('utf-8'))

    def do_GET(self):
        self._response(200, {
            "state": garage_state['state']
        })
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_body = json.loads(self.rfile.read(content_length))
        if post_body['state'] == 1 or post_body['state'] == 0:
            garage_state['state'] = post_body['state']
            self._response(202)
        else:
            self._response(400)

if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), Api)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    print("Server stopped.")