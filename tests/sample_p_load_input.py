"""
Created on Jan 21 13:55 2020

@author: nishit
"""

import json
import time

from senml import senml

l = 24
t = int(time.time())+100
v = 1
meas = []
for i in range(l):
    m = senml.SenMLMeasurement()
    m.name = "generic_1"
    m.value = v
    m.time = t
    meas.append(m)
    v += 1
    t += 3600

d = senml.SenMLDocument(meas)
s = d.to_json()
s = json.dumps(s)
print(s)

