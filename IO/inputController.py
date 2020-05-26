"""
Created on Jul 16 14:13 2018

@author: nishit
"""
import json

import os

import datetime
import concurrent.futures
import time

from math import floor

from IO.inputPreprocess import InputPreprocess
from optimization.baseValueDataReceiver import BaseValueDataReceiver
from optimization.genericDataReceiver import GenericDataReceiver
from optimization.genericEventDataReceiver import GenericEventDataReceiver
from utils_intern.constants import Constants
from utils_intern.messageLogger import MessageLogger


class InputController:

    def __init__(self, id, input_config_parser, config, control_frequency, horizon_in_steps, dT_in_seconds):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.stop_request = False
        self.input_config_parser = input_config_parser
        self.config = config
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.id = id

        self.optimization_data = self.init_optimization_data()
        self.prediction_mqtt_flags = {}
        self.pv_prediction_mqtt_flags = {}
        self.external_mqtt_flags = {}
        self.preprocess_mqtt_flags = {}
        self.event_mqtt_flags = {}
        self.sampling_mqtt_flags = {}
        self.generic_data_mqtt_flags = {}
        self.generic_names = None
        self.mqtt_timer = {}
        self.event_data = {}

        self.restart = self.input_config_parser.get_restart_value()

        mqtt_time_threshold = float(self.config.get("IO", "mqtt.detach.threshold", fallback=180))
        self.inputPreprocess = InputPreprocess(self.id, mqtt_time_threshold, config)

        data = self.input_config_parser.get_optimization_values()
        self.optimization_data.update(data)
        self.logger.debug("optimization data: " + str(self.optimization_data))

        sec_in_day = 24 * 60 * 60
        self.steps_in_day = floor(sec_in_day / dT_in_seconds)
        self.required_buffer_data = 0
        horizon_sec = horizon_in_steps * dT_in_seconds
        while horizon_sec > 0:
            self.required_buffer_data += self.steps_in_day
            horizon_sec = horizon_sec - sec_in_day

        self.data_receivers = {}
        self.event_data_receiver = {}
        self.sampling_data_receiver = {}
        for name, value in self.input_config_parser.name_params.keys():
            if "mqtt" in value.keys():
                params = value["mqtt"]
                option = params["option"]
                if option in ["predict", "pv_predict"]:
                    prediction_topic = config.get("IO", "forecast.topic")
                    prediction_topic = json.loads(prediction_topic)
                    prediction_topic["topic"] = prediction_topic["topic"] + name
                    self.data_receivers[name] = GenericDataReceiver(True, prediction_topic, config, name, self.id,
                                                                    self.required_buffer_data, self.dT_in_seconds)
                elif option == "preprocess":
                    self.logger.debug("params for preprocess " + name + " : " + str(params))
                    self.data_receivers[name] = BaseValueDataReceiver(False, params, config, name, self.id,
                                                                      self.required_buffer_data,
                                                                      self.dT_in_seconds)
                elif option == "event":
                    self.event_data_receiver[name] = GenericEventDataReceiver(False, params, config, name, self.id,
                                                                              self.inputPreprocess.event_received)
                elif option in "sampling":
                    self.sampling_data_receiver[name] = GenericDataReceiver(False, params, config, name, self.id,
                                                                            self.required_buffer_data,
                                                                            self.dT_in_seconds)
                else:
                    self.data_receivers[name] = GenericDataReceiver(False, params, config, name, self.id,
                                                                    self.required_buffer_data,
                                                                    self.dT_in_seconds)
            elif "datalist" in value.keys():
                self.data_receivers[name] = value["datalist"]

    def init_optimization_data(self):
        data = {}
        set_params = self.input_config_parser.get_set_params()
        if len(set_params) > 0:
            for key, value in set_params.items():
                v = self.input_config_parser.get_array(value)
                data[key] = {None: v}
        return data

    def read_input_data(self, id, name, file):
        """"/ usr / src / app / optimization / resources / 95c38e56d913 / file / p_load.txt"""
        data = {}
        path = os.path.join("/usr/src/app", "optimization/resources", str(id), "file", file)
        self.logger.debug("Data path: " + str(path))
        rows = []
        i = 0
        try:
            with open(path, "r") as file:
                rows = file.readlines()
        except Exception as e:
            self.logger.error("Read input file exception: " + str(e))
        for row in rows:
            data[i] = float(row)
            i += 1
        if len(data) == 0:
            self.logger.error("Data file empty " + name)
            return {}
        else:
            return {name: data}

    # TODO add support for file data set as well
    def get_sample(self, name, redisDB):
        self.logger.debug("name " + str(name))
        if name in self.sampling_data_receiver.keys():
            while True:
                try:
                    if redisDB.get("End ofw") == "True":
                        break
                    data, bucket_available, last_time = self.sampling_data_receiver[name].get_current_bucket_data(
                        steps=self.horizon_in_steps, wait_for_data=False, check_bucket_change=False)
                    if bucket_available:
                        return data
                    else:
                        self.logger.debug("bucket not available " + str(name))
                except Exception as e:
                    self.logger.error("error getting sample " + str(name) + " " + str(e))

    def get_data(self, preprocess, redisDB):
        redisDB.set(Constants.get_data_flow_key(self.id), True)
        # self.logger.info("sleep for data")
        # time.sleep(100)
        success = False
        while not success:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                try:
                    if redisDB.get("End ofw") == "True" or redisDB.get_bool("opt_stop_" + self.id):
                        break
                    current_bucket, _ = self.get_current_bucket()
                    self.logger.info("Get input data for bucket " + str(current_bucket))
                    futures = []
                    for name, receiver in self.data_receivers.items():
                        futures.append(executor.submit(self.fetch_mqtt_and_file_data, name, receiver, current_bucket,
                                                       self.horizon_in_steps))
                    time.sleep(15)
                    # The returned iterator raises a concurrent.futures.TimeoutError if __next__() is called and
                    # the result isn’t available after timeout seconds from the original call to as_completed()
                    for future in concurrent.futures.as_completed(futures, timeout=20):
                        success, read_data, mqtt_timer = future.result()
                        if success:
                            self.update_data(read_data)
                            self.mqtt_timer.update(mqtt_timer)
                        else:
                            self.logger.error("Success flag is False")
                            break
                except Exception as e:
                    self.logger.error(
                        "Error occured while getting data for bucket " + str(current_bucket) + ". " + str(e))
        if preprocess:
            self.inputPreprocess.preprocess(self.optimization_data, self.mqtt_timer)
        redisDB.set(Constants.get_data_flow_key(self.id), False)
        if self.restart:
            self.restart = False
        return {None: self.optimization_data.copy()}

    def fetch_mqtt_and_file_data(self, name, receiver, current_bucket, number_of_steps):
        try:
            self.logger.info("current bucket = " + str(current_bucket))
            data_available_for_bucket = True
            new_data = {}
            mqtt_timer = {}
            if isinstance(receiver, str):
                self.logger.debug("file name: " + str(receiver))
                data = self.read_input_data(self.id, name, receiver)
                new_data.update(data)
            else:
                self.logger.debug("mqtt True " + str(name))
                data, bucket_available, last_time = receiver.get_bucket_aligned_data(current_bucket,
                                                                                     number_of_steps)  # self.horizon_in_steps)
                self.logger.debug("Bucket available " + str(bucket_available) + " for " + str(name))
                if bucket_available:
                    self.logger.debug("Received data " + str(data))
                    mqtt_timer[name] = last_time
                    data = self.set_indexing(data)
                    self.logger.debug("Indexed data " + str(data))
                    if (self.restart and last_time > 0) or not self.restart:
                        new_data.update(data)
                data_available_for_bucket = bucket_available
            return (data_available_for_bucket, new_data, mqtt_timer)
        except Exception as e:
            self.logger.error("error in fetch_mqtt_and_file_data for " + str(e))
            raise e

    def update_data(self, data):
        self.logger.info("data for update : " + str(data))
        self.logger.debug("Length of data for update: " + str(len(data)))
        for k, v_new in data.items():
            new_data = {}
            if k in self.optimization_data.keys():
                v_old = self.optimization_data[k]
                if isinstance(v_old, dict) and isinstance(v_new, dict):
                    new_data.update(v_old)
                    new_data.update(v_new)
                    self.optimization_data[k] = new_data
                else:
                    new_data[k] = v_new
                    self.optimization_data.update(new_data)
            else:
                new_data[k] = v_new
                self.optimization_data.update(data)

    def Stop(self):
        self.stop_request = True
        self.logger.debug("data receiver exit start")
        self.exit_receiver(self.data_receivers)
        self.logger.debug("event receiver exit start")
        self.exit_receiver(self.event_data_receiver)
        self.logger.debug("sample receiver exit start")
        self.exit_receiver(self.sampling_data_receiver)

    def exit_receiver(self, receiver):
        if receiver is not None:
            for name in receiver.keys():
                receiver[name].exit()

    def set_indexing(self, data):
        new_data = {}
        for name, value in data.items():
            indexing = self.input_config_parser.get_variable_index(name)
            # default indexing will be set to "index" in baseDataReceiver
            if indexing == "None":
                if len(value) >= 1:
                    if isinstance(value, dict):
                        v = value[0]  # 0 is the key
                        new_data[name] = {None: v}
        data.update(new_data)
        return data

    def get_current_bucket(self):
        start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        current_time = datetime.datetime.now()
        time_since_start = (current_time - start_of_day).total_seconds()
        bucket = floor(time_since_start / self.dT_in_seconds)
        if bucket >= self.steps_in_day:
            bucket = self.steps_in_day - 1
        next_bucket = bucket + 1
        next_bucket_time = next_bucket * self.dT_in_seconds
        time_till_next_bucket = next_bucket_time - time_since_start
        if time_till_next_bucket < 30:
            time.sleep(time_till_next_bucket)
            bucket = next_bucket
            time_till_next_bucket = self.dT_in_seconds
        return bucket, time_till_next_bucket
