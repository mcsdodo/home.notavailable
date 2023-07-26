import requests

class StatusApiClient:
    def __init__(self, section):
        self.url = section['Url']
        client = section['CF-Access-Client-Id']
        secret = section['CF-Access-Client-Secret']
        self.headers = {'CF-Access-Client-Id' : client,'CF-Access-Client-Secret' : secret}
    def get_status(self):
        r = requests.get(self.url, headers=self.headers)
        return r
    def set_status(self, state):
        r = requests.post(self.url, headers=self.headers, json ={'state': state})
        return r
    def report_health(self):
        requests.head(self.url, headers=self.headers)