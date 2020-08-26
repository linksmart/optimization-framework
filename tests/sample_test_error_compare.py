import datetime
import json
import time
from configparser import RawConfigParser

from IO.radiation import Radiation
from prediction.rawDataReader import RawDataReader
from utils_intern.timeSeries import TimeSeries
import numpy as np


def adjust_data(value, base_data, current_timestamp, maxPV):
    new_data = []
    if len(base_data) > 0:
        closest_index = find_closest_prev_timestamp(base_data, current_timestamp)
        base_value = base_data[closest_index][1]
        factor = value - base_value
        print("closest index = " + str(base_value) + " value = " + str(value) + " factor = " + str(factor))
        for row in base_data:
            new_value = row[1] + factor
            if new_value < 0:
                new_value = 0
            if new_value > maxPV * 1000:
                new_value = maxPV * 1000
            new_data.append([row[0], new_value])
        return new_data


def find_closest_prev_timestamp(data, date):
    closest = 0
    for i, item in enumerate(data, 0):
        if item[0] <= date:
            closest = i
        else:
            break
    return closest


def predict(current_timestamp, base_data, maxPV, file_path):
    data = RawDataReader.get_raw_data_by_time(file_path, "P_PV", current_timestamp, current_timestamp + 60)
    print("pv data in run is " + str(data))
    if len(data) > 0:
        value = data[0][1]
        adjusted_data = adjust_data(value, base_data, current_timestamp, maxPV)
        return adjusted_data
    else:
        return None

def print_data(name, data):
    print()
    print(name)
    for row in data:
        print(row)

def extract_horizon_data(pv_data, current_timestamp, horizon_in_steps):
    new_data = []
    if len(pv_data) > 0:
        closest_index = find_closest_prev_timestamp(pv_data, current_timestamp)
        for i in range(horizon_in_steps):
            row = pv_data[closest_index]
            new_data.append(row)
            closest_index += 1
            if closest_index >= len(pv_data):
                closest_index = 0
    return new_data

def error(actual, predicted):
    """ Simple error """
    return actual - predicted

def rmse(actual, predicted):
    """ Root Mean Squared Error """
    return np.sqrt(mse(actual, predicted))

def mse(actual, predicted):
    """ Mean Squared Error """
    return np.mean(np.square(error(actual, predicted)))

def mae(actual, predicted):
    """ Mean Absolute Error """
    return np.mean(np.abs(error(actual, predicted)))

def compare(predicted, actual):

    if len(predicted) == len(actual):
        actual = np.asarray(actual)
        predicted = np.asarray(predicted)
        er = rmse(actual, predicted)

        return er
    else:
        print("length mismatch")
        return None

def get_timestamps(error_file):
    timestamps = []
    original_error = {}
    with open(error_file, "r") as f:
        data = f.readlines()
        for row in data:
            rows = row.split(",")
            timestamps.append(int(float(rows[0])))
            original_error[int(float(rows[0]))] = float(rows[1])
    return timestamps, original_error

def strip_timestamp(data):
    if len(data) > 0:
        new_data = []
        start_time = data[0][0]
        for t, v in data:
            new_data.append(v)
        return start_time, new_data
    return None, None

def get_error(current_timestamp):

    base_data = radiation.get_data(current_timestamp)
    predicted_data = predict(current_timestamp, base_data, maxPV, file_path)
    if predicted_data is not None:
        predicted_data = extract_horizon_data(predicted_data, current_timestamp, horizon_in_steps)
        timestamp, predicted_data = strip_timestamp(predicted_data)

        actual_data = RawDataReader.get_raw_data_by_time(file_path, "P_PV", current_timestamp,
                                                         current_timestamp + 3600 * 24)
        actual_data = TimeSeries.expand_and_resample(actual_data, dT_in_seconds)
        actual_data = actual_data[:horizon_in_steps]

        timestamp, actual_data = strip_timestamp(actual_data)

        error = compare(predicted_data, actual_data)
        return current_timestamp, error
    return None, None

config = RawConfigParser()
config.read("ConfigFile.properties")
maxPV = 4.68
dT_in_seconds = 300
horizon_in_steps = 288
location = {"city": "Fur", "country": "Denmark"}
file_path = "raw_data_P_PV.csv"
radiation = Radiation(config, maxPV, dT_in_seconds, location, horizon_in_steps)

timestamps, original_error = get_timestamps("error_data_P_PV.csv")

errors = []
for timestamp in timestamps:
    t, e = get_error(timestamp)
    if e is not None:
        errors.append([t,e])

for t, e in errors:
    if int(t) in original_error.keys():
        print(t, e, original_error[int(t)], original_error[int(t)] - e)
