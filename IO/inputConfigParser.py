"""
Created on Aug 03 14:22 2018

@author: nishit
"""
from functools import partial
import logging

import os
import numpy as np

from IO.ConfigParserUtils import ConfigParserUtils
from IO.constants import Constants
from optimization.ModelParamsInfo import ModelParamsInfo
from optimization.modelDerivedParameters import ModelDerivedParameters
from profev.EV import EV
from profev.ChargingStation import ChargingStation
from profev.EVPark import EVPark
from profev.MonteCarloSimulator import simulate
from utils_intern.messageLogger import MessageLogger

class InputConfigParser:

    def __init__(self, input_config_file, input_config_mqtt, model_name, id):
        self.logger = self.logger = MessageLogger.get_logger(__file__, id)
        self.model_name = model_name
        self.model_variables, self.param_key_list = ModelParamsInfo.get_model_param(self.model_name)
        self.input_config_file = input_config_file
        self.input_config_mqtt = input_config_mqtt
        self.base, self.derived = ModelDerivedParameters.get_derived_parameter_mapping(model_name)
        self.mqtt_params = {}
        self.generic_names = []
        self.generic_file_names = []
        # self.defined_prediction_names = ["P_Load", "P_Load_R", "P_Load_S", "P_Load_T", "Q_Load_R", "Q_Load_S", "Q_Load_T", "Q_Load"]
        self.defined_prediction_names = []
        self.defined_non_prediction_names = ["P_PV"]
        self.defined_external_names = ["SoC_Value"]
        self.defined_preprocess_names = []
        self.prediction_names = []
        self.non_prediction_names = []
        self.external_names = []
        self.preprocess_names = []
        self.set_params = {}
        self.config_parser_utils = ConfigParserUtils()
        self.extract_mqtt_params()
        self.car_park = None
        self.simulator = None
        self.optimization_params = self.extract_optimization_values()
        self.logger.debug("optimization_params: " + str(self.optimization_params))
        self.logger.info("generic names = " + str(self.generic_names))

    def read_mqtt_flags(self, value2, name):
        if isinstance(value2, dict):
            if "predict" in value2.keys():
                predict = bool(value2["predict"])
                if predict:
                    self.defined_prediction_names.append(name)
            if "preprocess" in value2.keys():
                preprocess = bool(value2["preprocess"])
                if preprocess:
                    self.defined_preprocess_names.append(name)

    def extract_mqtt_params(self):
        for key, value in self.input_config_mqtt.items():
            self.extract_mqtt_params_level(value)
        self.logger.info("params = " + str(self.mqtt_params))

    def extract_mqtt_params_level(self, value, base=""):
        for key2, value2 in value.items():
            mqtt = self.config_parser_utils.get_mqtt(value2)
            self.read_mqtt_flags(value2, base+key2)
            if mqtt is not None:
                self.mqtt_params[base+key2] = mqtt.copy()
                self.add_name_to_list(base+key2)
            elif len(base) == 0 and isinstance(value2, dict):
                self.extract_mqtt_params_level(value2, base=key2+"/")

    def add_name_to_list(self, key):
        if key in self.defined_prediction_names:
            self.prediction_names.append(key)
        elif key in self.defined_non_prediction_names:
            self.non_prediction_names.append(key)
        elif key in self.defined_external_names:
            self.external_names.append(key)
        elif key in self.defined_preprocess_names:
            self.preprocess_names.append(key)
        else:
            self.generic_names.append(key)

    def extract_optimization_values(self):
        data = {}
        for input_config in [self.input_config_file, self.input_config_mqtt]:
            for k, v in input_config.items():
                if isinstance(v, dict):
                    for k1, v1 in v.items():
                        if k1 == Constants.meta:
                            for k2, v2 in v1.items():
                                self.add_value_to_data(data, k2, v2)
                        elif k1 == Constants.SoC_Value and not isinstance(v1, dict):
                            indexing = "None"
                            if Constants.SoC_Value in self.model_variables.keys():
                                indexing = self.model_variables[Constants.SoC_Value]["indexing"]
                            if indexing == "index":
                                data[Constants.SoC_Value] = {int(0): float(v1)}
                            elif indexing == "None":
                                data[Constants.SoC_Value] = {None: float(v1)}
                        elif isinstance(v1, list):
                            self.add_name_to_list(k1)
                        elif k == "generic" and not isinstance(v1, dict):
                            self.logger.debug("Generic single value")
                            self.add_value_to_data(data, k1, v1)
                        elif isinstance(v1, dict):
                            data[k + "/" + k1] = v1
                        else:
                            try:
                                v1 = float(v1)
                            except ValueError:
                                pass
                            if isinstance(v1, float) and v1.is_integer():
                                v1 = int(v1)
                            data[k1] = {None: v1}
        #         pprint.pprint(data, indent=4)
        return data

    def add_value_to_data(self, data, k, v):
        try:
            v = float(v)
        except ValueError:
            pass
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        if k in self.model_variables.keys():
            if self.model_variables[k]["type"] == "Set":
                self.set_params[k] = v
            else:
                indexing = self.model_variables[k]["indexing"]
                if indexing == "index":
                    data[k] = {int(0): v}
                elif indexing == "None":
                    data[k] = {None: v}
        else:
            data[k] = {None: v}

    def get_forecast_flag(self, topic):
        if topic in self.mqtt_params:
            return True
        else:
            return False

    def get_generic_data_names(self):
        return self.generic_names

    def get_prediction_names(self):
        return self.prediction_names

    def get_non_prediction_names(self):
        return self.non_prediction_names

    def get_external_names(self):
        return self.external_names

    def get_preprocess_names(self):
        return self.preprocess_names

    def get_variable_index(self, name):
        if name in self.model_variables:
            return self.model_variables[name]["indexing"]
        else:
            return None

    def get_params(self, topic):
        return self.mqtt_params[topic]

    def get_optimization_values(self):
        return self.optimization_params

    def get_set_params(self):
        return self.set_params

    def check_keys_for_completeness(self):
        all_keys = []
        all_keys.extend(self.prediction_names)
        all_keys.extend(self.non_prediction_names)
        all_keys.extend(self.external_names)
        all_keys.extend(self.generic_names)
        all_keys.extend(self.preprocess_names)
        all_keys.extend(self.optimization_params.keys())
        all_keys.extend(self.set_params.keys())
        all_keys.append("dT")
        all_keys.append("T")
        self.logger.info("model_variables : "+ str(self.model_variables))
        self.logger.info("all_keys : " + str(all_keys))
        not_available_keys = []
        for key in self.model_variables.keys():
            if key not in all_keys and self.model_variables[key]["type"] in ["Set", "Param"] and key not in self.derived:
                not_available_keys.append(key)
        for key in self.base:
            if key not in all_keys:
                not_available_keys.append(key)
        return not_available_keys
