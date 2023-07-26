import requests

class StatusApiClient:
    def __init__(self, section):
        self.url = section['Url']
        client = section['CF-Access-Client-Id']
        secret = section['CF-Access-Client-Secret']
        self.headers = {'CF-Access-Client-Id' : client,'CF-Access-Client-Secret' : secret}
        print(self.headers)
    def get_status(self):
        r = requests.get(self.url, headers=self.headers)
        return r
    def set_status(self, state):
        r = requests.post(self.url, headers=self.headers, json ={'state': state})
        print(state)
        return r
    def report_health(self):
        # https://stackoverflow.com/a/45601591/1712948
        try:
            requests.head(self.url, timeout=0.0000000001)
        except requests.exceptions.ReadTimeout:
            pass