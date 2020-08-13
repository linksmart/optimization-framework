"""
Created on Aug 03 14:02 2018

@author: nishit
"""
import datetime
import json
import os
import threading

import time
from queue import Queue

from IO.influxDBmanager import InfluxDBManager
from IO.radiation import Radiation
from IO.redisDB import RedisDB
from optimization.pvForecastPublisher import PVForecastPublisher
from prediction.predictionDataManager import PredictionDataManager
from utils_intern.constants import Constants
from utils_intern.messageLogger import MessageLogger
from utils_intern.timeSeries import TimeSeries
from utils_intern.utilFunctions import UtilFunctions


class PVPrediction(threading.Thread):

    def __init__(self, config, output_config, input_config_parser, id, control_frequency, horizon_in_steps, dT_in_seconds, generic_name):
        super().__init__()
        self.logger = MessageLogger.get_logger(__name__, id)
        self.logger.debug("PV prediction class")
        self.stopRequest = threading.Event()
        self.config = config
        self.q = Queue(maxsize=0)
        self.generic_name = generic_name
        self.control_frequency = control_frequency
        self.control_frequency = int(self.control_frequency / 2)
        self.control_frequency = 60
        self.id = id
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.old_predictions = {}
        self.output_config = output_config
        self.influxDB = InfluxDBManager()
        self.raw_data_file_container = os.path.join("/usr/src/app", "prediction/resources", self.id,
                                                    "raw_data_" + str(generic_name) + ".csv")

        self.prediction_data_file_container = os.path.join("/usr/src/app", "prediction/resources", self.id,
                                                           "prediction_data_" + str(generic_name) + ".csv")

        self.error_result_file_path = os.path.join("/usr/src/app", "prediction/resources", self.id,
                                                   "error_data_" + str(generic_name) + ".csv")

        self.redisDB = RedisDB()
        raw_pv_data_topic = input_config_parser.get_params(generic_name)
        opt_values = input_config_parser.get_optimization_values()

        city = "Bonn"
        country = "Germany"
        try:
            city = opt_values["City"][None]
            country = opt_values["Country"][None]
        except Exception:
            self.logger.error("City or country not present in pv meta")

        location = {"city":city,"country":country}

        self.maxPV = float(opt_values["PV_Inv_Max_Power"][None])
        pv_forecast_topic = config.get("IO", "forecast.topic")
        pv_forecast_topic = json.loads(pv_forecast_topic)
        pv_forecast_topic["topic"] = pv_forecast_topic["topic"] + self.generic_name

        self.radiation = Radiation(config, self.maxPV, dT_in_seconds, location, horizon_in_steps)

        self.max_file_size_mins = config.getint("IO", "pv.raw.data.file.size", fallback=10800)

        self.copy_prediction_file_data_to_influx()
        from prediction.rawLoadDataReceiver import RawLoadDataReceiver
        self.raw_data = RawLoadDataReceiver(raw_pv_data_topic, config, 1, self.raw_data_file_container,
                                            generic_name, self.id, False, self.max_file_size_mins, self.influxDB)

        self.pv_forecast_pub = PVForecastPublisher(pv_forecast_topic, config, id, 60,
                                                   horizon_in_steps, dT_in_seconds, self.q)
        self.pv_forecast_pub.start()

        self.prediction_save_thread = threading.Thread(target=self.save_to_file_cron)
        self.prediction_save_thread.start()

        from prediction.errorReporting import ErrorReporting
        error_topic_params = config.get("IO", "error.topic")
        error_topic_params = json.loads(error_topic_params)
        error_topic_params["topic"] = error_topic_params["topic"] + generic_name
        self.error_reporting = ErrorReporting(config, id, generic_name, dT_in_seconds, control_frequency,
                                              horizon_in_steps, self.prediction_data_file_container,
                                              self.raw_data_file_container, error_topic_params,
                                              self.error_result_file_path, self.output_config, self.influxDB)
        self.error_reporting.start()

    def Stop(self):
        self.logger.debug("Stopping pv forecast thread")
        self.stopRequest.set()
        if self.pv_forecast_pub is not None:
            self.pv_forecast_pub.Stop()
        if self.raw_data is not None:
            self.raw_data.exit()
        if self.error_reporting:
            self.error_reporting.Stop()
        self.logger.debug("pv prediction thread exit")

    def run(self):
        self.logger.debug("Running pv prediction")
        while not self.stopRequest.is_set():
            if not self.redisDB.get_bool(Constants.get_data_flow_key(self.id)):
                time.sleep(30)
                continue
            self.logger.debug("pv prediction data flow true")
            try:
                start = time.time()
                data = self.raw_data.get_raw_data()
                self.logger.debug("pv data in run is "+str(data))
                if len(data) > 0:
                    value = data[0][1]
                    current_timestamp = data[0][0]
                    self.logger.debug("pv received timestamp "+str(current_timestamp)+ " val "+str(value))
                    base_data = self.radiation.get_data(current_timestamp)
                    shifted_base_data = TimeSeries.shift_by_timestamp(base_data, current_timestamp, self.dT_in_seconds)
                    self.logger.debug("base_data = "+str(shifted_base_data))
                    adjusted_data = self.adjust_data(shifted_base_data, value, current_timestamp)
                    predicted_data = self.extract_horizon_data(adjusted_data)
                    self.logger.debug("pv predicted timestamp "+str(predicted_data[0][0]))
                    if predicted_data is not None and len(predicted_data) > 0:
                        self.q.put(predicted_data)
                        self.old_predictions[int(predicted_data[0][0])] = predicted_data
                start = self.control_frequency - (time.time() - start)
                if start > 0:
                    time.sleep(start)
            except Exception as e:
                self.logger.error(str(self.generic_name) + " prediction thread exception " + str(e))

    def adjust_data(self, shifted_base_data, value, current_timestamp):
        new_data = []
        if len(shifted_base_data) > 0:
            closest_index = self.find_closest_prev_timestamp(shifted_base_data, current_timestamp)
            self.logger.debug("closest index = "+str(closest_index))
            base_value = shifted_base_data[closest_index][1]
            #if value < 1:
                #value = 1
            factor = value - base_value
            self.logger.debug("closest index value = " + str(base_value)+" mqtt value = "+ str(value) +" factor = "+str(factor))
            for row in shifted_base_data:
                new_value = row[1]+factor
                if new_value < 0:
                    new_value = 0
                if new_value > self.maxPV*1000:
                    new_value = self.maxPV*1000
                new_data.append([row[0], new_value])
            self.logger.debug("new_data = "+str(new_data))
            return new_data

    def find_closest_prev_timestamp(self, data, date):
        closest = 0
        for i, item in enumerate(data, 0):
            if item[0] <= date:
                closest = i
            else:
                break
        return closest

    def find_closest_next_timestamp(self, data, date):
        closest = len(data) - 1
        for i in reversed(range(len(data))):
            item = data[i]
            if item[0] > date:
                closest = i
            else:
                break
        return closest

    def extract_horizon_data(self, predicted_data):
        new_data = []
        if len(predicted_data) > 0:
            current_timestamp = datetime.datetime.now().timestamp()
            closest_index = self.find_closest_prev_timestamp(predicted_data, current_timestamp)
            for i in range(self.horizon_in_steps):
                row = predicted_data[closest_index]
                new_data.append([row[0], row[1]])
                closest_index += 1
                if closest_index >= len(predicted_data):
                    closest_index = 0
            return new_data
        else:
            return None

    def save_to_file_cron(self):
        self.logger.debug("Started save file cron")
        while True and not self.stopRequest.is_set():
            self.old_predictions = PredictionDataManager.save_predictions_dict_to_influx(self.influxDB,
                                                                                         self.old_predictions,
                                                                                          self.horizon_in_steps,
                                                                                          self.generic_name, self.id)
            time.sleep(UtilFunctions.get_sleep_secs(1,0,0))
            #time.sleep(UtilFunctions.get_sleep_secs(0, 2, 0))

    def copy_prediction_file_data_to_influx(self):
        data_file = PredictionDataManager.get_prediction_data(self.prediction_data_file_container, self.generic_name)
        if len(data_file) > 0:
            data = PredictionDataManager.save_predictions_dict_to_influx(self.influxDB, data_file,
                                                                    self.horizon_in_steps, self.generic_name, self.id)
            if len(data) == 0:
                PredictionDataManager.del_predictions_to_file(self.prediction_data_file_container, self.generic_name)
