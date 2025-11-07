# this runs on the PiZero in garage. Updates code

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess

class MyServer(BaseHTTPRequestHandler):
    def _set_headers(self, status, message=None):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        if message is not None:
            self.wfile.write(json.dumps(message, default=str).encode('utf-8'))
        
    def do_POST(self):
        if self.path == '/update':
            output = subprocess.run(["/usr/bin/bash", "/home/dodo/home.notavailable/garage.controller.api/deploy.sh"], cwd='/home/dodo/home.notavailable/', capture_output=True, text=True)
            if (output.returncode == 0):
                self._set_headers(200, output.stdout.encode())
            else:
                self._set_headers(500, output.stderr.encode())
        else:
            self._set_headers(404)
    
    def do_HEAD(self):
        self._set_headers(200)
    
if __name__ == "__main__":
    HOST_NAME = "0.0.0.0"
    SERVER_PORT = 8081
    webServer = HTTPServer((HOST_NAME, SERVER_PORT), MyServer)
    print("Server started http://%s:%s" % (HOST_NAME, SERVER_PORT))

    try:
        webServer.serve_forever()
    finally:
        pass

    webServer.server_close()
    print("Server stopped.")