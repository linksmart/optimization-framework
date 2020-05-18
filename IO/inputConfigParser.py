"""
Created on Aug 03 14:22 2018

@author: nishit
"""
import json
import os

from IO.ConfigParserUtils import ConfigParserUtils
from utils_intern.constants import Constants
from optimization.ModelParamsInfo import ModelParamsInfo
from optimization.modelDerivedParameters import ModelDerivedParameters

from utils_intern.messageLogger import MessageLogger


class InputConfigParser:

    def __init__(self, input_config, model_name, id, optimization_type, persist_path, restart):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.model_name = model_name
        self.model_variables, self.param_key_list = ModelParamsInfo.get_model_param(self.model_name)
        self.input_config = input_config
        self.base, self.derived = ModelDerivedParameters.get_derived_parameter_mapping(model_name, optimization_type)
        self.mqtt_params = {}
        self.generic_names = []
        self.generic_file_names = []
        self.defined_prediction_names = []
        self.defined_pv_prediction_names = ["P_PV"]
        self.defined_external_names = ["SoC_Value"]
        self.defined_preprocess_names = []
        self.defined_event_names = []
        self.defined_sampling_names = []
        self.prediction_names = []
        self.pv_prediction_names = []
        self.external_names = []
        self.preprocess_names = []
        self.event_names = []
        self.sampling_names = []
        self.dual_source_names = []
        self.set_params = {}
        self.car_park = None
        self.simulator = None

        #self.extract_mqtt_params()
        self.optimization_params = self.extract_optimization_values()
        self.restart = restart
        if restart:
            self.read_persisted_data(persist_path)
        self.logger.debug("optimization_params: " + str(self.optimization_params))
        self.logger.info("generic names = " + str(self.generic_names))

    def extract_mqtt_params(self):
        for key, value in self.input_config.items():
            self.extract_mqtt_params_level(value)
        self.logger.info("params = " + str(self.mqtt_params))

    def extract_mqtt_params_level(self, value, base=""):
        for key2, value2 in value.items():
            mqtt = ConfigParserUtils.get_mqtt(value2)
            if base == "P_PV/":
                print("§", key2, value2, mqtt)
            if mqtt is not None:
                self.read_mqtt_flags(value2, base + key2)
                self.mqtt_params[base + key2] = mqtt.copy()
                self.add_name_to_list(base + key2)
            elif len(base) == 0 and isinstance(value2, list):
                print("1 "+str(key2))
                for mqtts in value2:
                    print(mqtts)
                    self.extract_mqtt_params_level(mqtts, base=base + key2 + "/")
                self.extract_set_info(key2, value2)
            elif isinstance(value2, dict):
                self.extract_mqtt_params_level(value2, base=base + key2 + "/")

    def read_mqtt_flags(self, mqtt, indexed_name):
        if isinstance(mqtt, dict):
            if "option" in mqtt.keys():
                value = mqtt["option"]
                if value == "predict":
                    self.defined_prediction_names.append(indexed_name)
                elif value == "pv_predict":
                    self.defined_pv_prediction_names.append(indexed_name)
                elif value == "preprocess":
                    self.defined_preprocess_names.append(indexed_name)
                elif value == "event":
                    self.defined_event_names.append(indexed_name)
                elif value == "sampling":
                    self.defined_sampling_names.append(indexed_name)

    def get_indexed_name(self, name, index):
        return (name, index)

    def extract_optimization_values(self):
        data = {}
        for header, header_value in self.input_config.items():
            if isinstance(header_value, dict):
                for name, name_value in header_value.items():
                    if name == Constants.meta:
                        for k2, v2 in name_value.items():
                            self.add_value_to_data(data, k2, v2)
                    elif isinstance(name_value, list):
                        for i, list_item in enumerate(name_value):
                            indexed_name = self.get_indexed_name(name, i)
                            if "datalist" in list_item.keys() and "mqtt" in list_item.keys():
                                mqtt = list_item["mqtt"]
                                mqtt = ConfigParserUtils.get_mqtt(mqtt)
                                if mqtt is not None:
                                    self.read_mqtt_flags(mqtt, indexed_name)
                                    self.dual_source_names.append(indexed_name)
                                self.add_name_to_list(indexed_name)
                            elif "mqtt" in list_item.keys():
                                mqtt = list_item["mqtt"]
                                mqtt = ConfigParserUtils.get_mqtt(mqtt)
                                if mqtt is not None:
                                    self.read_mqtt_flags(mqtt, indexed_name)
                                    self.add_name_to_list(indexed_name)
                            elif "datalist" in list_item.keys():
                                self.add_name_to_list(indexed_name)
                            if "meta" in list_item.keys():
                                for meta_key, meta_value in list_item["meta"].items():
                                    self.add_value_to_data(data, meta_key, meta_value)
                        self.extract_set_info(name, name_value)
                    elif header == "generic" and not isinstance(name_value, dict):
                        self.logger.debug("Generic single value")
                        self.add_value_to_data(data, name, name_value)
                    elif isinstance(name_value, dict):
                        # data[k + "/" + k1] = v1
                        data[name] = self.remove_mqtt_source(name_value)
                    else:
                        try:
                            name_value = float(name_value)
                        except ValueError:
                            pass
                        if isinstance(name_value, float) and name_value.is_integer():
                            name_value = int(name_value)
                        data[name] = {None: name_value}
        #         pprint.pprint(data, indent=4)
        return data

    def add_name_to_list(self, key):
        if key in self.defined_prediction_names:
            self.prediction_names.append(key)
        elif key in self.defined_pv_prediction_names:
            self.pv_prediction_names.append(key)
        elif key in self.defined_external_names:
            self.external_names.append(key)
        elif key in self.defined_preprocess_names:
            self.preprocess_names.append(key)
        elif key in self.defined_event_names:
            self.event_names.append(key)
        elif key in self.defined_sampling_names:
            self.sampling_names.append(key)
        else:
            self.generic_names.append(key)

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
                if len(indexing) == 0:
                    data[k] = {None: v}
                else:
                    temp_data = {}
                    for index in range(len(indexing)):
                        if index == 0:
                            temp_data = {0: v}
                        else:
                            temp_data[0] : temp_data
                    data[k] = temp_data
        else:
            data[k] = {None: v}

    def extract_set_info(self, key, value):
        try:
            if isinstance(value, list):
                count = len(value)
                if self.model_variables[key]["type"] == "Param":
                    indexing = self.model_variables[key]["indexing"]
                    if len(indexing) == count:
                        for index in indexing:
                            if index not in self.set_params.keys():
                                self.set_params[index] = count
                    else:
                        print("error")
        except Exception as e:
            print("error")

    def remove_mqtt_source(self, v1):
        if isinstance(v1, dict):
            if "mqtt" in v1.keys():
                return {}
            else:
                for k2 in v1.keys():
                    v1[k2] = self.remove_mqtt_source(v1[k2])
                return v1
        else:
            return v1

    def read_persisted_data(self, persist_path):
        if os.path.exists(persist_path):
            self.logger.debug("Persisted path exists: " + str(persist_path))
            files = os.listdir(persist_path)
            for file in files:
                try:
                    with open(os.path.join(persist_path, file), "r") as f:
                        data = f.readlines()
                        print(data)
                        if ".json" in file:
                            data = data[0]
                            data = json.loads(data)
                            print(data)
                            if isinstance(data, list):
                                for row in data:
                                    if isinstance(row, dict):
                                        print(row)
                                        self.optimization_params.update(row)
                            elif isinstance(data, dict):
                                self.optimization_params.update(data)
                except Exception as e:
                    self.logger.error("Error reading persisted file " + str(persist_path))
        else:
            self.logger.debug("Persisted path does not exist: " + str(persist_path))

    def check_keys_for_completeness(self):
        all_keys = []
        all_keys.extend(self.prediction_names)
        all_keys.extend(self.pv_prediction_names)
        all_keys.extend(self.external_names)
        all_keys.extend(self.generic_names)
        all_keys.extend(self.preprocess_names)
        all_keys.extend(self.optimization_params.keys())
        all_keys.extend(self.set_params.keys())
        all_keys.append("dT")
        all_keys.append("T")
        all_keys.append("Max_Charging_Power_kW")
        self.logger.info("model_variables : " + str(self.model_variables))
        self.logger.info("all_keys : " + str(all_keys))
        not_available_keys = []
        for key in self.model_variables.keys():
            if key not in all_keys and self.model_variables[key]["type"] in ["Set",
                                                                             "Param"] and key not in self.derived:
                not_available_keys.append(key)
        for key in self.base:
            if key not in all_keys:
                not_available_keys.append(key)
        return not_available_keys

    def get_restart_value(self):
        return self.restart

    def get_forecast_flag(self, topic):
        if topic in self.mqtt_params:
            return True
        else:
            return False

    def get_generic_data_names(self):
        return self.generic_names

    def get_prediction_names(self):
        return self.prediction_names

    def get_pv_prediction_names(self):
        return self.pv_prediction_names

    def get_external_names(self):
        return self.external_names

    def get_preprocess_names(self):
        return self.preprocess_names

    def get_event_names(self):
        return self.event_names

    def get_sampling_names(self):
        return self.sampling_names

    def get_variable_index(self, name):
        if name in self.model_variables:
            return self.model_variables[name]["indexing"]
        else:
            return "empty"

    def get_params(self, topic):
        return self.mqtt_params[topic]

    def get_optimization_values(self):
        return self.optimization_params

    def get_set_params(self):
        return self.set_params
