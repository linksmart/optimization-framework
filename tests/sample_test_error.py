import datetime
import random
from configparser import RawConfigParser

from tests.testerrorrep import ErrorReporting


def create_mock_raw_data(start_time, steps):
    data = []
    time = float(int(start_time))
    for i in range(steps):
        data.append([time, -i])
        time += 60
    return data

def save_raw_to_file(data, file_path):
    try:
        print("Saving raw data to file "+str(file_path))
        new_data = []
        for item in data:
            line = ','.join(map(str, item[:2])) + "\n"
            new_data.append(line)
            new_data = new_data[-10080:] # 7 days data
        with open(file_path, 'w+') as file:
                file.writelines(new_data)
        file.close()
    except Exception as e:
        print(e)

def create_mock_prediction_data(start_time, steps, dT, start_val):
    data = {}
    time = datetime.datetime.fromtimestamp(start_time).replace(microsecond=0)
    for i in range(steps):
        data[time] = start_val-i*(dT/60)
        time += datetime.timedelta(dT)
    return data

def save_predictions_to_file(predictions, horizon_in_steps, prediction_data_file_container):
    if len(predictions) > 0:
        try:
            result = predictions.items()
            result = sorted(result)
            start_time = result[0][0].timestamp()
            data = []
            for i in range(horizon_in_steps):
                value = result[i][1]
                if value >= 0:
                    value = 0
                data.append(str(value))
            values = ",".join(data)
            values = str(start_time)+","+values+"\n"
            with open(prediction_data_file_container, 'a+') as file:
                    file.writelines(values)
        except Exception as e:
            print("failed to save_to_file "+ str(e))

def create_mocks(num_of_sequence, dT, steps, raw_data_file, predicted_file):
    current_time = datetime.datetime.now().replace(second=0, microsecond=0)
    start_time = current_time - datetime.timedelta(seconds=dT*steps*num_of_sequence)
    raw_data = create_mock_raw_data(start_time.timestamp(), steps*num_of_sequence*(int(dT/60)))
    save_raw_to_file(raw_data, raw_data_file)
    time = start_time
    start_value = 0
    for i in range(steps*num_of_sequence):
        predicted_data = create_mock_prediction_data(time.timestamp(), steps, dT, start_value)
        save_predictions_to_file(predicted_data, steps, predicted_file)
        time += datetime.timedelta(seconds=dT)
        start_value -= dT/60

raw_data_file = "raw_data_P_PV.csv"
predicted_file = "prediction_data_P_PV.csv"
error_file = "error_data_P_PV.csv"
config = RawConfigParser()
config.read("ConfigFile.properties")
maxPV = 4.68
dT_in_seconds = 300
horizon_in_steps = 288

error_report = ErrorReporting(config, "abcd", "P_PV", dT_in_seconds, dT_in_seconds, horizon_in_steps,
                 predicted_file, raw_data_file, None, error_file, None)

result = error_report.compare_data(dT_in_seconds)

print(result)