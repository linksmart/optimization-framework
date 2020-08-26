import json
import time

from senml import senml

print(time.time())

b = senml.SenMLMeasurement()
b.name = "/chargers/"
m = senml.SenMLMeasurement()
m.name = "ev1"
m.value = 1
m.time = int(time.time())

d = senml.SenMLDocument([m], base=b)
s = d.to_json()
s = json.dumps(s)

print(s)

b = senml.SenMLMeasurement()
b.name = "chargers/charger2"
m = senml.SenMLMeasurement()
m.name = "ev2/recharge"
m.value = 1
m.time = int(time.time())

d = senml.SenMLDocument([m], base=b)
s = d.to_json()
s = json.dumps(s)

print(s)

b = senml.SenMLMeasurement()
b.name = "chargers/charger1"
m = senml.SenMLMeasurement()
m.name = "ev1/SoC"
m.value = 0.2
m.time = int(time.time())

d = senml.SenMLDocument([m], base=b)
s = d.to_json()
s = json.dumps(s)

print(s)

b = senml.SenMLMeasurement()
b.name = "chargers/charger2"
m = senml.SenMLMeasurement()
m.name = "ev2/SoC"
m.value = 0.2
m.time = int(time.time())

d = senml.SenMLDocument([m], base=b)
s = d.to_json()
s = json.dumps(s)

print(s)
