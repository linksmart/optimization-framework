"""
Created on Nov 07 15:37 2019

@author: nishit
"""
import datetime
import json
import threading

import os

import numpy as np
from senml import senml

from IO.dataPublisher import DataPublisher
from prediction.rawDataReader import RawDataReader
from utils_intern.messageLogger import MessageLogger
from utils_intern.timeSeries import TimeSeries


class ErrorReporting(DataPublisher):

    def __init__(self, config, id, topic_name, dT_in_seconds, control_frequency, horizon_in_steps,
                 prediction_data_file_container, raw_data_file_container, topic_params, error_result_file_path):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.raw_data_file_container = raw_data_file_container
        self.raw_data = RawDataReader()
        self.stopRequest = threading.Event()
        self.topic_name = topic_name
        self.id = id
        self.prediction_data_file_container = prediction_data_file_container
        self.error_result_file_path = error_result_file_path
        super().__init__(True, topic_params, config, control_frequency, id)

    def get_data(self):
        try:
            rmse, mae, time = self.compare_data(time_delay=0)
            if rmse is not None and mae is not None and time is not None:
                self.save_to_file(rmse, mae, time)
                return self.to_senml(rmse, mae, time)
            else:
                return None
        except Exception as e:
            self.logger.error("error computing error report data " + str(e))

    def to_senml(self, rmse, mae, time):
        meas = []
        meas.append(self.get_senml_meas(rmse, time, "rmse"))
        meas.append(self.get_senml_meas(mae, time, "mae"))
        doc = senml.SenMLDocument(meas)
        val = doc.to_json()
        return json.dumps(val)

    def get_senml_meas(self, value, time, name):
        if not isinstance(time, float):
            time = float(time.timestamp())
        meas = senml.SenMLMeasurement()
        meas.time = time
        meas.value = value
        meas.name = name
        return meas

    def save_to_file(self, rmse, mae, time):
        try:
            with open(self.error_result_file_path, "a+") as f:
                line = str(time)+","+str(rmse)+","+str(mae)+"\n"
                f.writelines(line)
        except Exception as e:
            self.logger.error("error adding to file "+str(self.error_result_file_path)+ " "+ str(e))

    def get_predicted_data(self, timestamp):
        start_time, values = self.read_predictions(timestamp)
        if start_time is not None and values is not None:
            t = start_time
            new_data = []
            for v in values:
                new_data.append([t,float(v)])
                t += self.dT_in_seconds
            return start_time, self.convert_time_to_date(new_data)
        return None, None

    def read_predictions(self, timestamp):
        if os.path.exists(self.prediction_data_file_container):
            line = None
            with open(self.prediction_data_file_container, "r") as f:
                data = f.readlines()
                for row in data:
                    start_time = float(row.split(",")[0])
                    if start_time < timestamp:
                        continue
                    else:
                        line = row
                        break
            if line:
                values = line.split(",")
                start_time = float(values[0])
                values = values[1:]
                return start_time, values
        return None, None

    def read_raw_data(self, start_time):
        end_time = start_time + self.dT_in_seconds*self.horizon_in_steps
        data = self.raw_data.get_raw_data_by_time(self.raw_data_file_container, self.topic_name, start_time, end_time)
        data = TimeSeries.expand_and_resample(data, self.dT_in_seconds)
        data = data[:-1]
        return self.convert_time_to_date(data)

    def convert_time_to_date(self, data):
        new_data = []
        for row in data:
            t = row[0]
            v = row[1]
            t = datetime.datetime.fromtimestamp(t)
            new_data.append([t,v])
        new_data = sorted(new_data)
        return new_data

    def compare_data(self, time_delay):
        timestamp = self.get_timestamp() - time_delay
        self.logger.debug("start_time "+str(timestamp))
        start_time, predicted_data = self.get_predicted_data(timestamp)
        if start_time is not None and predicted_data is not None:
            self.logger.debug("start_time " + str(start_time))
            actual_data = self.read_raw_data(start_time)
            if actual_data is not None:
                self.logger.debug("length "+str(len(actual_data))+" "+str(len(predicted_data)))
                if len(actual_data) == len(predicted_data):
                    if len(actual_data) > 0:
                        timestamp_matches = True
                        actual = []
                        predicted = []
                        for i in range(len(actual_data)):
                            at = actual_data[i][0]
                            pt = predicted_data[i][0]
                            if at != pt:
                                self.logger.error(str(at.timestamp()) + " != " + str(pt.timestamp()) + " diff = " + str((at - pt)))
                                timestamp_matches = False
                                break
                            else:
                                actual.append(actual_data[i][0])
                                predicted.append(predicted_data[i][0])
                        if timestamp_matches:
                            actual = np.asarray(actual)
                            predicted = np.asarray(predicted)
                            rmse = self.rmse(actual, predicted)
                            mae = self.mae(actual, predicted)
                            return rmse, mae, start_time
        return None, None, None

    def get_timestamp(self):
        current_time = datetime.datetime.now()
        current_time = current_time.replace(second=0, microsecond=0)
        current_time = current_time - datetime.timedelta(seconds=self.dT_in_seconds*self.horizon_in_steps)
        return current_time.timestamp()

    def error(self, actual, predicted):
        """ Simple error """
        return actual - predicted

    def rmse(self, actual, predicted):
        """ Root Mean Squared Error """
        return np.sqrt(self.mse(actual, predicted))

    def mse(self, actual, predicted):
        """ Mean Squared Error """
        return np.mean(np.square(self.error(actual, predicted)))

    def mae(self, actual, predicted):
        """ Mean Absolute Error """
        return np.mean(np.abs(self.error(actual, predicted)))