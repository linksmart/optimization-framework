"""
Created on Aug 03 14:02 2018

@author: nishit
"""
import datetime
import json
import threading

import time
from queue import Queue

from senml import senml

from IO.dataReceiver import DataReceiver
from IO.radiation import Radiation
from optimization.genericDataReceiver import GenericDataReceiver
from optimization.pvForecastPublisher import PVForecastPublisher
from utils_intern.messageLogger import MessageLogger


class PVPrediction(threading.Thread):

    def __init__(self, config, input_config_parser, id, control_frequency, horizon_in_steps, dT_in_seconds, generic_name):
        super().__init__()
        self.logger = MessageLogger.get_logger(__name__, id)
        self.logger.debug("PV prediction class")
        self.stopRequest = threading.Event()
        self.config = config
        self.q = Queue(maxsize=0)
        self.generic_name = generic_name
        self.control_frequency = control_frequency
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

        maxPV = float(opt_values["PV_Inv_Max_Power"][None])
        pv_forecast_topic = config.get("IO", "forecast.topic")
        pv_forecast_topic = json.loads(pv_forecast_topic)
        pv_forecast_topic["topic"] = pv_forecast_topic["topic"] + self.generic_name
        self.base_data = {}

        radiation = Radiation(config, maxPV, dT_in_seconds, location)
        self.pv_thread = threading.Thread(target=self.get_pv_data_from_source, args=(radiation,))
        self.pv_thread.start()

        self.raw_data = GenericDataReceiver(False, raw_pv_data_topic, config, self.generic_name, id, 1, dT_in_seconds)

        self.pv_forecast_pub = PVForecastPublisher(pv_forecast_topic, config, id, control_frequency,
                                                   horizon_in_steps, dT_in_seconds, self.q)
        self.pv_forecast_pub.start()

    def get_pv_data_from_source(self, radiation):
        """PV Data fetch thread. Runs at 23:30 every day"""
        while not self.stopRequest.is_set():
            try:
                self.logger.info("Fetching pv data from radiation api")
                data = radiation.get_data()
                pv_data = json.loads(data)
                self.base_data = pv_data
                self.logger.debug("pv data = "+str(self.base_data))
                delay = self.get_delay_time(23, 30)
                while delay > 100 or not self.stopRequest.is_set():
                    time.sleep(30)
                    delay -= 30
                if self.stopRequest.is_set():
                    break
                delay = self.get_delay_time(23, 30)
                time.sleep(delay)
            except Exception as e:
                self.logger.error(e)
                time.sleep(10)

    def get_delay_time(self, hour, min):
        date = datetime.datetime.now()
        requestedTime = datetime.datetime(date.year, date.month, date.day, hour, min, 0)
        if requestedTime < date:
            requestedTime = requestedTime + datetime.timedelta(days=1)
        return requestedTime.timestamp() - date.timestamp()

    def Stop(self):
        self.logger.debug("Stopping pv forecast thread")
        self.stopRequest.set()
        if self.pv_forecast_pub is not None:
            self.pv_forecast_pub.Stop()
        if self.raw_data is not None:
            self.raw_data.exit()
        self.logger.debug("pv prediction thread exit")

    def run(self):
        while not self.stopRequest.is_set():
            try:
                start = time.time()
                data, bucket_available, self.last_time = self.raw_data.get_current_bucket_data(steps=1)
                self.logger.debug("pv data in run is "+str(data))
                value = data[self.generic_name][0]
                self.logger.debug("base_data = "+str(self.base_data))
                adjusted_data = self.adjust_data(value)
                self.q.put(adjusted_data)
                start = self.control_frequency - (time.time() - start)
                if start > 0:
                    time.sleep(start)
            except Exception as e:
                self.logger.error(str(self.generic_name) + " prediction thread exception " + str(e))

    def adjust_data(self, value):
        new_data = []
        if len(self.base_data) > 0:
            current_timestamp = datetime.datetime.now().timestamp()
            closest_index = self.find_closest_prev_timestamp(self.base_data, current_timestamp)
            base_value = self.base_data[closest_index][1]
            factor = base_value - value
            self.logger.debug("closest index = " + str(base_value)+" value = "+ str(value) +" factor = "+str(factor))
            for row in self.base_data:
                new_value = row[1]-factor
                if new_value < 0:
                    new_value = 0
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

