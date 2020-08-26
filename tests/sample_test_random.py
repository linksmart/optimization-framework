import datetime
import json
import time
from configparser import RawConfigParser

from IO.radiation import Radiation
from utils_intern.timeSeries import TimeSeries


def adjust_data(shifted_base_data, value, current_timestamp):
    new_data = []
    if len(shifted_base_data) > 0:
        closest_index = find_closest_prev_timestamp(shifted_base_data, current_timestamp)
        print("closest index = " + str(closest_index))
        base_value = shifted_base_data[closest_index][1]
        # if value < 1:
        # value = 1
        factor = value - base_value
        print("closest index = " + str(base_value) + " value = " + str(value) + " factor = " + str(factor))
        for row in shifted_base_data:
            new_value = row[1] + factor
            if new_value < 0:
                new_value = 0
            if new_value > maxPV * 1000:
                new_value = maxPV * 1000
            new_data.append([row[0], new_value])
        print("new_data = " + str(new_data))
        return new_data


def find_closest_prev_timestamp(data, date):
    closest = 0
    for i, item in enumerate(data, 0):
        if item[0] <= date:
            closest = i
        else:
            break
    return closest

def extract_horizon_data(predicted_data, t):
    new_data = []
    if len(predicted_data) > 0:
        current_timestamp = t
        closest_index = find_closest_prev_timestamp(predicted_data, current_timestamp)
        for i in range(horizon_in_steps):
            row = predicted_data[closest_index]
            new_data.append([row[0], row[1]])
            closest_index += 1
            if closest_index >= len(predicted_data):
                closest_index = 0
        return new_data
    else:
        return None


t = 1585842180
value = 55.23666666666666
config = RawConfigParser()
config.read("ConfigFile.properties")
maxPV = 3.12
dT_in_seconds = 300
horizon_in_steps = 288
location = {"city": "Fur", "country": "Denmark"}
radiation = Radiation(config, maxPV, dT_in_seconds, location, horizon_in_steps)

base_data = radiation.get_data(t)
print(base_data)

shifted_base_data = TimeSeries.shift_by_timestamp(base_data, t, dT_in_seconds)
print(shifted_base_data)
adjusted_data = adjust_data(shifted_base_data, value, t)
predicted_data = extract_horizon_data(adjusted_data, t)
print(predicted_data)
print(len(predicted_data))

print(t)
print(predicted_data[0][0])