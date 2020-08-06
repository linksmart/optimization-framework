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

    def __init__(self, id, input_config_parser, config, control_frequency, horizon_in_steps, dT_in_seconds, preprocess):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.stop_request = False
        self.input_config_parser = input_config_parser
        self.config = config
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.id = id
        self.preprocess = preprocess
        self.mqtt_timer = {}
        self.event_data = {}
        self.optimization_data = self.init_set_params()
        data = self.input_config_parser.get_optimization_values()
        self.optimization_data.update(data)
        self.logger.debug("optimization data 1: " + str(self.optimization_data))
        self.restart = self.input_config_parser.get_restart_value()
        self.steps_in_day, self.required_buffer_data = self.calculate_required_buffer()

        if self.preprocess:
            mqtt_time_threshold = float(self.config.get("IO", "mqtt.detach.threshold", fallback=180))
            self.inputPreprocess = InputPreprocess(self.id, mqtt_time_threshold, config,
                                                   self.input_config_parser.name_params,
                                                   data)

        self.data_receivers, self.event_data_receivers, self.sampling_data_receivers = self.initialize_data_receivers()
        self.logger.debug("optimization data 2: " + str(self.optimization_data))


    def initialize_data_receivers(self):
        data_receivers = {}
        event_data_receivers = {}
        sampling_data_receivers = {}
        for indexed_name, value in self.input_config_parser.name_params.items():
            name = indexed_name[0]
            index = indexed_name[1]
            name_with_index = name + "~" + str(index)
            if "mqtt" in value.keys():
                params = value["mqtt"]
                option = params["option"]
                if option in ["predict", "pv_predict", "pv_predict_lstm"]:
                    prediction_topic = self.config.get("IO", "forecast.topic")
                    prediction_topic = json.loads(prediction_topic)
                    prediction_topic["topic"] = prediction_topic["topic"] + name_with_index
                    data_receivers[indexed_name] = GenericDataReceiver(True, prediction_topic, self.config, name_with_index, self.id,
                                                                    self.required_buffer_data, self.dT_in_seconds)
                elif option == "preprocess":
                    self.logger.debug("params for preprocess " + name_with_index + " : " + str(params))
                    data_receivers[indexed_name] = BaseValueDataReceiver(False, params, self.config, name_with_index, self.id,
                                                                      self.required_buffer_data,
                                                                      self.dT_in_seconds)
                elif option == "event":
                    event_data_receivers[indexed_name] = GenericEventDataReceiver(False, params, self.config, name_with_index, self.id,
                                                                              self.inputPreprocess.event_received)
                elif option == "sampling":
                    sampling_data_receivers[indexed_name] = GenericDataReceiver(False, params, self.config, name_with_index, self.id,
                                                                            self.required_buffer_data,
                                                                            self.dT_in_seconds)
                else:
                    data_receivers[indexed_name] = GenericDataReceiver(False, params, self.config, name_with_index, self.id,
                                                                    self.required_buffer_data,
                                                                    self.dT_in_seconds)
            elif "datalist" in value.keys():
                data_receivers[indexed_name] = value["datalist"]

        return data_receivers, event_data_receivers, sampling_data_receivers

    def calculate_required_buffer(self):
        sec_in_day = 24 * 60 * 60
        steps_in_day = floor(sec_in_day / self.dT_in_seconds)
        required_buffer_data = 0
        horizon_sec = self.horizon_in_steps * self.dT_in_seconds
        while horizon_sec > 0:
            required_buffer_data += steps_in_day
            horizon_sec = horizon_sec - sec_in_day
        return steps_in_day, required_buffer_data

    # TODO: need to think
    def init_set_params(self):
        data = {}
        set_params = self.input_config_parser.get_set_params()
        if len(set_params) > 0:
            for key, value in set_params.items():
                v = self.input_config_parser.get_array(value)
                data[key] = {None: v}
        return data

    def read_input_data(self, id, name, file):
        """"/ usr / src / app / optimization / resources / 95c38e56d913 / file / p_load.txt"""
        path = os.path.join("/usr/src/app", "optimization/resources", str(id), "file", file)
        self.logger.debug("Data path: " + str(path))
        i = 0
        try:
            data = {}
            with open(path, "r") as file:
                rows = file.readlines()
                for row in rows:
                    data[i] = float(row)
                    i += 1
                return data
        except Exception as e:
            self.logger.error("Read input file exception: " + str(e))

    # TODO add support for file data set as well
    def get_sample(self, name, redisDB):
        self.logger.debug("name " + str(name))
        if name in self.sampling_data_receivers.keys():
            while True:
                try:
                    if redisDB.get("End ofw") == "True":
                        break
                    data, bucket_available, last_time = self.sampling_data_receivers[name].get_current_bucket_data(
                        steps=self.horizon_in_steps, wait_for_data=False, check_bucket_change=False)
                    if bucket_available:
                        return data
                    else:
                        self.logger.debug("bucket not available " + str(name))
                except Exception as e:
                    self.logger.error("error getting sample " + str(name) + " " + str(e))

    def get_data(self, redisDB):
        redisDB.set(Constants.get_data_flow_key(self.id), True)
        self.logger.info("sleep for data")
        time.sleep(100)
        if len(self.data_receivers) > 0:
            success = False
            while not success:
                try:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        if redisDB.get("End ofw") == "True" or redisDB.get_bool("opt_stop_" + self.id):
                            break
                        current_bucket, time_till_next_bucket = self.get_current_bucket()
                        per_future_wait_time = time_till_next_bucket/len(self.data_receivers) - 2
                        self.logger.info("Get input data for bucket " + str(current_bucket))
                        futures = []
                        for name, receiver in self.data_receivers.items():
                            futures.append(executor.submit(self.fetch_mqtt_and_file_data, name, receiver, current_bucket,
                                                           self.horizon_in_steps))
                        # The returned iterator raises a concurrent.futures.TimeoutError if __next__() is called and
                        # the result isn’t available after timeout seconds from the original call to as_completed()
                        for future in concurrent.futures.as_completed(futures, timeout=per_future_wait_time):
                            success, read_data, mqtt_timer = future.result()
                            if success:
                                self.update_data(read_data)
                                self.mqtt_timer.update(mqtt_timer)
                            else:
                                self.logger.error("Success flag is False")
                                break
                except Exception as e:
                    success = False
                    self.logger.error(
                        "Error occured while getting data for bucket " + str(current_bucket) + " " + str(e))
            self.logger.info("opt data: "+json.dumps(self.optimization_data))
            if self.preprocess:
                self.inputPreprocess.preprocess(self.optimization_data, self.mqtt_timer)
        redisDB.set(Constants.get_data_flow_key(self.id), False)
        if self.restart:
            self.restart = False
        return {None: self.optimization_data.copy()}

    def fetch_mqtt_and_file_data(self, name, receiver, current_bucket, number_of_steps):
        try:
            self.logger.info("current bucket = " + str(current_bucket))
            data_available_for_bucket = True
            data = {}
            mqtt_timer = {}
            if isinstance(receiver, str):
                self.logger.debug("file name: " + str(receiver))
                data = self.read_input_data(self.id, name, receiver)
                data = {name: data}
            else:
                self.logger.debug("mqtt True " + str(name))
                received_data, bucket_available, last_time = receiver.get_bucket_aligned_data(current_bucket, number_of_steps)
                self.logger.debug("Bucket available " + str(bucket_available) + " for " + str(name))
                if bucket_available:
                    self.logger.debug("Received data " + str(received_data))
                    mqtt_timer[name] = last_time
                    data_value = {}
                    for key, value in received_data.items():
                        data_value = value
                        break
                    if not isinstance(receiver, BaseValueDataReceiver):
                        data_value = self.set_indexing(data_value, name)
                    self.logger.debug("Indexed data " + str(data_value))
                    if not self.restart or (self.restart and last_time > 0):
                        data = {name: data_value}
                data_available_for_bucket = bucket_available
            return (data_available_for_bucket, data, mqtt_timer)
        except Exception as e:
            self.logger.error("error in fetch_mqtt_and_file_data for " + str(name)+ " " + str(e))
            raise e

    def get_array_of_none(self, length):
        data = []
        for i in range(length):
            data.append(None)
        return data

    # TODO: make changes
    def update_data(self, data):
        self.logger.info("data for update : " + str(data))
        self.logger.debug("Length of data for update: " + str(len(data)))
        for indexed_name, v_new in data.items():
            name = indexed_name[0]
            index = indexed_name[1]
            set_name, set_length = self.input_config_parser.get_index_set_length(name)
            self.logger.info("set name "+str(set_name)+" "+str(set_length))
            new_data = {}
            if set_name:
               new_data[index] = v_new
            if name in self.optimization_data.keys():
                old_data = self.optimization_data[name]
                if isinstance(old_data, dict):
                    old_data.update(new_data)
                    self.optimization_data[name] = old_data
            else:
                if len(new_data) == 0:
                    self.optimization_data[name] = v_new
                else:
                    self.optimization_data[name] = new_data

    def Stop(self):
        self.stop_request = True
        self.logger.debug("data receiver exit start")
        self.exit_receiver(self.data_receivers)
        self.logger.debug("event receiver exit start")
        self.exit_receiver(self.event_data_receivers)
        self.logger.debug("sample receiver exit start")
        self.exit_receiver(self.sampling_data_receivers)

    def exit_receiver(self, receiver):
        if receiver is not None:
            for name in receiver.keys():
                receiver[name].exit()

    # TODO:make changes
    def set_indexing(self, data_value, name):
        indexing = self.input_config_parser.get_variable_index(name)
        self.logger.debug("set index: "+str(name)+" "+str(indexing)+" "+str(data_value))
        # default indexing will be set to "index" in baseDataReceiver
        if len(indexing) == 0:
            if len(data_value) >= 1 and isinstance(data_value, dict):
                if 0 in data_value.keys():
                    return {None: data_value[0]}  # 0 is the key
                else:
                    for key, value in data_value.items():
                        return {None: value}
        return data_value

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