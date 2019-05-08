"""
Created on Jul 16 14:13 2018

@author: nishit
"""
import json

import os

import datetime
from math import floor

from optimization.SoCValueDataReceiver import SoCValueDataReceiver
from optimization.genericDataReceiver import GenericDataReceiver
from utils_intern.messageLogger import MessageLogger


class InputController:

    def __init__(self, id, input_config_parser, config, control_frequency, horizon_in_steps, dT_in_seconds):
        self.logger = MessageLogger.get_logger(__file__, id)
        self.stop_request = False
        self.optimization_data = {}
        self.input_config_parser = input_config_parser
        self.logger.debug("Config parser: " + str(self.input_config_parser))
        self.config = config
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.id = id
        self.prediction_mqtt_flags = {}
        self.non_prediction_mqtt_flags = {}
        self.external_mqtt_flags = {}
        self.generic_data_mqtt_flags = {}
        self.generic_names = None

        self.parse_input_config()
        self.set_timestep_data()

        sec_in_day = 24*60*60
        self.steps_in_day = floor(sec_in_day/dT_in_seconds)
        self.required_buffer_data = 0
        horizon_sec = horizon_in_steps * dT_in_seconds
        while horizon_sec > 0:
            self.required_buffer_data += self.steps_in_day
            horizon_sec = horizon_sec - sec_in_day

        self.internal_receiver = {}
        for name, flag in self.prediction_mqtt_flags.items():
            if flag:
                """ should be prediction topic instead of load"""
                prediction_topic = config.get("IO", "forecast.topic")
                prediction_topic = json.loads(prediction_topic)
                prediction_topic["topic"] = prediction_topic["topic"] + name
                self.internal_receiver[name] = GenericDataReceiver(True, prediction_topic, config, name,
                                                                   self.id, self.required_buffer_data, self.dT_in_seconds)
        for name, flag in self.non_prediction_mqtt_flags.items():
            if flag:
                non_prediction_topic = config.get("IO", "forecast.topic")
                non_prediction_topic = json.loads(non_prediction_topic)
                non_prediction_topic["topic"] = non_prediction_topic["topic"] + name
                self.internal_receiver[name] = GenericDataReceiver(True, non_prediction_topic, config, name,
                                                                   self.id, self.required_buffer_data, self.dT_in_seconds)
        # ESS data
        self.external_data_receiver = {}
        for topic, flag in self.external_mqtt_flags.items():
            if flag:
                if topic == "SoC_Value":
                    params = self.input_config_parser.get_params("SoC_Value")
                    self.logger.debug("params for MQTT SoC_Value: " + str(params))
                    self.external_data_receiver[topic] = SoCValueDataReceiver(False, params, config, self.id,
                                                                              self.required_buffer_data, self.dT_in_seconds)

        self.generic_data_receiver = {}
        if len(self.generic_data_mqtt_flags) > 0:
            for generic_name, mqtt_flag in self.generic_data_mqtt_flags.items():
                if mqtt_flag:
                    topic = self.input_config_parser.get_params(generic_name)
                    self.generic_data_receiver[generic_name] = GenericDataReceiver(False, topic, config, generic_name,
                                                                                   self.id, self.required_buffer_data, self.dT_in_seconds)

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
        self.optimization_data.update(data)

        self.prediction_names = self.input_config_parser.get_prediction_names()
        self.set_mqtt_flags(self.prediction_names, self.prediction_mqtt_flags)

        self.non_prediction_names = self.input_config_parser.get_non_prediction_names()
        self.set_mqtt_flags(self.non_prediction_names, self.non_prediction_mqtt_flags)

        self.external_names = self.input_config_parser.get_external_names()
        self.set_mqtt_flags(self.external_names, self.external_mqtt_flags)

        self.generic_names = self.input_config_parser.get_generic_data_names()
        self.set_mqtt_flags(self.generic_names, self.generic_data_mqtt_flags)

    def set_mqtt_flags(self, names, mqtt_flags):
        self.logger.debug("names = " + str(names))
        if names is not None and len(names) > 0:
            for name in names:
                mqtt_flags[name] = self.input_config_parser.get_forecast_flag(name)

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
        else:
            self.optimization_data[topic] = data

    def get_data(self):
        success = False
        while not success:
            current_bucket = self.get_current_bucket()
            self.logger.info("Get input data for bucket "+str(current_bucket))
            success = self.fetch_mqtt_and_file_data(self.prediction_mqtt_flags, self.internal_receiver, [], [], current_bucket)
            if success:
                success = self.fetch_mqtt_and_file_data(self.non_prediction_mqtt_flags, self.internal_receiver, [], [], current_bucket)
            if success:
                success = self.fetch_mqtt_and_file_data(self.external_mqtt_flags, self.external_data_receiver, [], ["SoC_Value"], current_bucket)
            if success:
                success = self.fetch_mqtt_and_file_data(self.generic_data_mqtt_flags, self.generic_data_receiver, [], [], current_bucket)
        return {None: self.optimization_data.copy()}

    def fetch_mqtt_and_file_data(self, mqtt_flags, receivers, mqtt_exception_list, file_exception_list, current_bucket):
        self.logger.debug("mqtt flags " + str(mqtt_flags))
        self.logger.info("current bucket = "+str(current_bucket))
        data_available_for_bucket = True
        if mqtt_flags is not None:
            for name, mqtt_flag in mqtt_flags.items():
                if mqtt_flag:
                    self.logger.debug("mqtt True " + str(name))
                    if name not in mqtt_exception_list:
                        data, bucket_available = receivers[name].get_bucket_aligned_data(current_bucket, self.horizon_in_steps)
                        if not bucket_available:
                            data_available_for_bucket = False
                            self.logger.info(str(name)+" data for bucket "+str(current_bucket)+" not available")
                            break
                        data = self.set_indexing(data)
                        self.optimization_data.update(data)
                else:
                    self.logger.debug("file name: " + str(name))
                    if name not in file_exception_list:
                        self.read_input_data(self.id, name, name + ".txt")
        return data_available_for_bucket

    def Stop(self):
        self.stop_request = True
        self.logger.debug("internal receiver exit start")
        self.exit_receiver(self.internal_receiver)
        self.logger.debug("external receiver exit start")
        self.exit_receiver(self.external_data_receiver)
        self.logger.debug("generic receiver exit start")
        self.exit_receiver(self.generic_data_receiver)

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