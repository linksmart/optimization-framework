import json
import time

from senml import senml

def to_senml(base, name, value):
    if base:
        b = senml.SenMLMeasurement()
        b.name = base
    else:
        b = None
    m = senml.SenMLMeasurement()
    m.name = name
    m.value = value
    m.time = int(time.time())

    d = senml.SenMLDocument([m], base=b)
    s = d.to_json()
    s = json.dumps(s)

    print(s)

print(time.time())

to_senml("chargers/charger0", "ev0/recharge", 1)
to_senml("chargers/charger0", "ev0/SoC", 0.3)
to_senml("chargers/charger1", "ev1/SoC", 0.2)
to_senml("chargers/charger2", "ev2/recharge", 1)
to_senml("", "P_Load", 8.7)
to_senml("", "P_PV", 6718.666666666667)

