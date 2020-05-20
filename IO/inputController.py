"""
Created on Jul 16 14:13 2018

@author: nishit
"""
import json

import os

import datetime
import concurrent.futures
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
        self.optimization_data = {}
        self.input_config_parser = input_config_parser
        self.config = config
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.id = id
        self.prediction_mqtt_flags = {}
        self.pv_prediction_mqtt_flags = {}
        self.external_mqtt_flags = {}
        self.preprocess_mqtt_flags = {}
        self.event_mqtt_flags = {}
        self.sampling_mqtt_flags = {}
        self.generic_data_mqtt_flags = {}
        self.generic_names = None
        self.mqtt_timer = {}
        mqtt_time_threshold = float(self.config.get("IO", "mqtt.detach.threshold", fallback=180))
        self.inputPreprocess = InputPreprocess(self.id, mqtt_time_threshold, config)
        self.event_data = {}
        self.restart = self.input_config_parser.get_restart_value()
        self.set_timestep_data()
        self.parse_input_config()

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

    def set_timestep_data(self):
        self.optimization_data["N"] = {None: [0]}
        self.optimization_data["dT"] = {None: self.dT_in_seconds}
        
        T = self.get_array(self.horizon_in_steps)
        self.optimization_data["T"] = {None: T}
        
        set_params = self.input_config_parser.get_set_params()
        if len(set_params) > 0:
            for key, value in set_params.items():
                v = self.get_array(value)
                self.optimization_data[key] = {None: v}
    
    def get_array(self, len):
        a = []
        for i in range(len):
            a.append(i)
        return a
    
    def parse_input_config(self):
        data = self.input_config_parser.get_optimization_values()
        self.logger.debug("param data: " + str(data))
        self.optimization_data.update(data)
        self.logger.debug("optimization data: " + str(self.optimization_data))

    def read_input_data(self, id, topic, file):
        """"/ usr / src / app / optimization / resources / 95c38e56d913 / p_load.txt"""
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
            self.logger.error("Data file empty " + topic)
            return {}
        else:
            return {topic: data}
    
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
        timeout_exception = True
        while timeout_exception:
            success = False
            executor = concurrent.futures.ThreadPoolExecutor()#(max_workers=3)
            while not success:
                if redisDB.get("End ofw") == "True" or redisDB.get_bool("opt_stop_" + self.id):
                    timeout_exception = False
                    break
                self.logger.debug("Starting getting data")
                current_bucket = self.get_current_bucket()
                self.logger.info("Get input data for bucket " + str(current_bucket))
                self.logger.debug("optimization_data before getting new values " + str(self.optimization_data))
                try:
                    
        
                    futures = []

                    futures.append(executor.submit(self.fetch_mqtt_and_file_data, self.prediction_mqtt_flags,
                                                   self.data_receivers, current_bucket,
                                                   self.horizon_in_steps))
                    
                    try:
            
                        for future in concurrent.futures.as_completed(futures):#,timeout=30):
                            try:
                                success, read_data, mqtt_timer = future.result()
                                self.logger.debug("Success flag for future in wait data: " + str(success))
                                if success:
                                    self.update_data(read_data)
                                    self.mqtt_timer.update(mqtt_timer)
                                    timeout_exception = False
                                else:
                                    self.logger.error("Success flag is False")
                                    timeout_exception = True
                                    break
                            except Exception as exc:
                                self.logger.error("input fetch data caused an exception: " + str(exc))
                                timeout_exception = True
                                break
                    except Exception as e:
                        self.logger.error("Timeout in getting data. " + str(e))
                        timeout_exception = True
                        #self.logger.error("Executor shutdown in getting data")
                        #executor.shutdown(wait=False)
                except Exception as e:
                    self.logger.error("Error occured while getting data for bucket " + str(current_bucket) + ". " + str(e))
                    timeout_exception = True

            self.logger.error("Executor shutdown")
            executor.shutdown(wait=True)
            if timeout_exception:
                self.logger.debug("timeout_exception flag "+str(timeout_exception))
                continue
            else:
                self.logger.debug("timeout_exception flag " + str(timeout_exception))
                break
            
        if preprocess:
            self.inputPreprocess.preprocess(self.optimization_data, self.mqtt_timer)
        redisDB.set(Constants.get_data_flow_key(self.id), False)
        if self.restart:
            self.restart = False
        return {None: self.optimization_data.copy()}
    
    def fetch_mqtt_and_file_data(self, mqtt_flags, receivers, current_bucket, number_of_steps):
        try:
            self.logger.debug("mqtt flags " + str(mqtt_flags))
            self.logger.info("current bucket = " + str(current_bucket))
            data_available_for_bucket = True
            new_data = {}
            mqtt_timer = {}
            
            if mqtt_flags is not None:
                for name, mqtt_flag in mqtt_flags.items():
                    if mqtt_flag:
                        self.logger.debug("mqtt True " + str(name))
                        data, bucket_available, last_time = receivers[name].get_bucket_aligned_data(current_bucket,
                                                                                                    number_of_steps)  # self.horizon_in_steps)
                        self.logger.debug("Received data " + str(data))
                        mqtt_timer[name] = last_time
                        self.logger.debug("mqtt_timer " + str(mqtt_timer))
                        self.logger.debug("Bucket available " + str(bucket_available) + " for " + str(name))
                        if not bucket_available:
                            data_available_for_bucket = False
                            self.logger.info(
                                str(name) + " data for bucket " + str(current_bucket) + " not available")
                            break
                        data = self.set_indexing(data)
                        self.logger.debug("Indexed data " + str(data))
                        if (self.restart and last_time > 0) or not self.restart:
                            new_data.update(data)
                    else:
                        self.logger.debug("file name: " + str(name))
                        data = self.read_input_data(self.id, name, name + ".txt")
                        new_data.update(data)
            self.logger.debug(
                "data_available_for_bucket: " + str(data_available_for_bucket) + " for " + str(mqtt_flags))
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
        self.logger.debug("internal receiver exit start")
        self.exit_receiver(self.internal_receiver)
        self.logger.debug("external receiver exit start")
        self.exit_receiver(self.external_data_receiver)
        self.logger.debug("generic receiver exit start")
        self.exit_receiver(self.generic_data_receiver)
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
        bucket = floor((current_time - start_of_day).total_seconds() / self.dT_in_seconds)
        if bucket >= self.steps_in_day:
            bucket = self.steps_in_day - 1
        return bucket