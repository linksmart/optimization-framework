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

from IO.ConfigParserUtils import ConfigParserUtils
from IO.dataPublisher import DataPublisher
from prediction.predictionDataManager import PredictionDataManager
from prediction.rawDataReader import RawDataReader
from utils_intern.messageLogger import MessageLogger
from utils_intern.timeSeries import TimeSeries


class ErrorReporting(DataPublisher):

    def __init__(self, config, id, topic_name, dT_in_seconds, control_frequency, horizon_in_steps,
                 prediction_data_file_container, raw_data_file_container, topic_params, error_result_file_path,
                 output_config):
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
        self.output_config = output_config
        self.topic_params = topic_params
        if self.update_topic_params():
            super().__init__(False, self.topic_params, config, control_frequency, id)
        else:
            super().__init__(True, self.topic_params, config, control_frequency, id)

    def update_topic_params(self):
        mqtt_params = ConfigParserUtils.extract_mqtt_params_output(self.output_config, "error_calculation", True)
        if self.topic_name in mqtt_params.keys():
            self.topic_params = mqtt_params[self.topic_name]
            self.logger.debug("Error_Calculation topic param updated - "+str(self.topic_params))
            return True
        return False

    def get_data(self):
        try:
            results = self.compare_data(time_delay=0)
            self.logger.debug("len of error cal results = "+str(len(results)))
            self.logger.debug("error cal results = "+str(results))
            if len(results) > 0:
                self.save_to_file(results)
                PredictionDataManager.del_predictions_from_file(list(results.keys()), self.prediction_data_file_container,
                                                                self.topic_name)
                return self.to_senml(results)
            else:
                return None
        except Exception as e:
            self.logger.error("error computing error report data " + str(e))

    def to_senml(self, results):
        meas = []
        base = None
        if "base_name" in self.topic_params:
            base = senml.SenMLMeasurement()
            base.name = self.topic_params["base_name"]
        for time, errors in results.items():
            rmse = errors["rmse"]
            mae = errors["mae"]
            meas.append(self.get_senml_meas(rmse, time, self.topic_name+"/rmse"))
            meas.append(self.get_senml_meas(mae, time, self.topic_name+"/mae"))
        doc = senml.SenMLDocument(meas, base=base)
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

    def save_to_file(self, results):
        try:
            new_data = []
            for time, errors in results.items():
                rmse = errors["rmse"]
                mae = errors["mae"]
                line = str(time)+","+str(rmse)+","+str(mae)+"\n"
                new_data.append(line)
            with open(self.error_result_file_path, "a+") as f:
                f.writelines(new_data)
            self.logger.debug("saved error cal to file " + str(self.error_result_file_path))
        except Exception as e:
            self.logger.error("error adding to file "+str(self.error_result_file_path)+ " "+ str(e))

    def format_predicted_data(self, start_time, values):
        if start_time is not None and values is not None:
            t = start_time
            new_data = []
            for v in values:
                new_data.append([t,float(v)])
                t += self.dT_in_seconds
            return self.convert_time_to_date(new_data)
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
        results = {}
        predicitons = PredictionDataManager.get_predictions_before_timestamp(self.prediction_data_file_container,
                                                                             self.topic_name, timestamp)
        self.logger.debug("count of predictions = "+str(len(predicitons)))
        for start_time, prediction in predicitons.items():
            predicted_data = self.format_predicted_data(start_time, prediction)
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
                                    actual.append(float(actual_data[i][1]))
                                    predicted.append(float(predicted_data[i][1]))
                            if timestamp_matches:
                                actual = np.asarray(actual)
                                predicted = np.asarray(predicted)
                                rmse = self.rmse(actual, predicted)
                                mae = self.mae(actual, predicted)
                                results[start_time] = {"rmse":rmse, "mae":mae}
        return results

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