import configparser
from statusapiclient import StatusApiClient

config = configparser.ConfigParser()
config.read('garage.controller.api/config.ini')
section = config['status.api']

client = StatusApiClient(section)

r = client.set_status('CLOSED')
print("set responded", r.status_code)

r = client.get_status()
print("get responded",r.json()['state'])

r = client.set_status('OPENING')
print("set responded", r.status_code)

r = client.get_status()
print("get responded", r.json()['state'])
