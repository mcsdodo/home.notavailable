import requests

class StatusApiClient:
    def __init__(self, section):
        self.url = section['Url']
    def get_status(self):
        try:
            r = requests.get(self.url, headers=self.headers, timeout=15)
            return r
        finally:
            pass
    def set_status(self, state):
        try:
            requests.post(self.url, headers=self.headers, json ={'state': state}, timeout=15)
        finally:
            pass
    def report_health(self, state = ""):
        try:
            url = self.url + state
            requests.head(url, headers=self.headers, timeout=15)
        finally:
            pass