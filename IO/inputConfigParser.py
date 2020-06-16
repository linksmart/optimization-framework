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

    def __init__(self, input_config, model_name, id, optimization_type, dT_in_seconds, horizon_in_steps, persist_path, restart):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.model_name = model_name
        self.model_variables, self.param_key_list = ModelParamsInfo.get_model_param(self.model_name)
        self.input_config = input_config
        self.base, self.derived = ModelDerivedParameters.get_derived_parameter_mapping(model_name, optimization_type)
        self.generic_names = []
        self.prediction_names = []
        self.pv_prediction_names = []
        self.preprocess_names = []
        self.event_names = []
        self.sampling_names = []
        self.set_params = {}
        self.name_params = {}
        self.car_park = None
        self.simulator = None

        data = {"dT": {None: dT_in_seconds},
                "T": {None: self.get_array(horizon_in_steps)}}
        self.optimization_params = self.extract_optimization_values(data)
        self.convert_string_key_to_tuple()
        self.meta_values = self.extract_meta_values()
        self.add_meta_values_to_opt_params()
        self.restart = restart
        if restart:
            self.read_persisted_data(persist_path)
        self.logger.debug("optimization_params: " + str(self.optimization_params))
        self.logger.debug("name_params: " + str(self.name_params))

    def get_array(self, len):
        a = []
        for i in range(len):
            a.append(i)
        return a

    def extract_mqtt_and_datalist_params(self, value, base=""):
        extracted = False
        for i, (key2, value2) in enumerate(value.items()):
            if base == "":
                name = key2
            else:
                name = base + "/" + key2
            if isinstance(value2, dict):
                if not self.extract_name_params(name, value2):
                    extracted = extracted or self.extract_mqtt_and_datalist_params(value2, base=name)
                else:
                    extracted = True
            else:
                if base not in self.name_params.keys():
                    self.name_params[base] = {}
                self.name_params[base][key2] = value2
                extracted = True
        return extracted

    def get_indexed_name(self, name, index):
        return (name, index)

    def extract_optimization_values(self, data):
        for header, header_value in self.input_config.items():
            if isinstance(header_value, dict):
                for j, (name, name_value) in enumerate(header_value.items()):
                    if name == Constants.meta:
                        for k2, v2 in name_value.items():
                            self.add_value_to_data(data, k2, v2)
                    elif isinstance(name_value, list):
                        for i, list_item in enumerate(name_value):
                            indexed_name = self.get_indexed_name(name, i)
                            self.extract_name_params(indexed_name, list_item)
                        self.extract_set_info(name, name_value)
                    elif header == "generic" and not isinstance(name_value, dict):
                        self.logger.debug("Generic single value")
                        self.add_value_to_data(data, name, name_value)
                    elif isinstance(name_value, dict):
                        indexed_name = str(j) + "~" + name
                        if not self.extract_mqtt_and_datalist_params(name_value, base=indexed_name):
                            data[name] = self.remove_mqtt_and_datalist(name_value)
                    else:
                        data[name] = {None: self.type_cast_value(name_value)}
        return data

    def extract_name_params(self, indexed_name, data_dict):
        extracted = False
        self.name_params[indexed_name] = {}
        if "mqtt" in data_dict.keys():
            mqtt = data_dict["mqtt"]
            mqtt = ConfigParserUtils.get_mqtt(mqtt)
            if mqtt is not None:
                self.name_params[indexed_name]["mqtt"] = mqtt.copy()
                option = mqtt["option"]
                self.add_name_to_list(indexed_name, option)
                extracted = True
        if "datalist" in data_dict.keys():
            self.name_params[indexed_name]["datalist"] = self.get_file_name(indexed_name)
            self.add_name_to_list(indexed_name)
            extracted = True
        if "meta" in data_dict.keys():
            for meta_key, meta_value in data_dict["meta"].items():
                meta_value = self.type_cast_value(meta_value)
                self.name_params[indexed_name][meta_key] = meta_value
        for key, value in data_dict.items():
            if key not in ["mqtt", "datalist", "meta"]:
                print(key)
                self.name_params[indexed_name][key] = value
        return extracted

    def get_file_name(self, indexed_name):
        if isinstance(indexed_name, str):
            file_name = indexed_name.replace("/", "~") + ".txt"
        else:
            file_name = indexed_name[0] + "~" + str(indexed_name[1]) + ".txt"
        return file_name

    def add_name_to_list(self, indexed_name, option=None):
        if option == "predict":
            self.prediction_names.append(indexed_name)
        elif option == "pv_predict":
            self.pv_prediction_names.append(indexed_name)
        elif option == "preprocess":
            self.preprocess_names.append(indexed_name)
        elif option == "event":
            self.event_names.append(indexed_name)
        elif option == "sampling":
            self.sampling_names.append(indexed_name)
        else:
            self.generic_names.append(indexed_name)

    def type_cast_value(self, v):
        try:
            v = float(v)
        except ValueError:
            pass
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        return v

    def add_value_to_data(self, data, k, v):
        v = self.type_cast_value(v)
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
                if key in self.model_variables.keys() and self.model_variables[key]["type"] == "Param":
                    indexing = self.model_variables[key]["indexing"]
                    if len(indexing) == 2:
                        set_name = indexing[0]
                        if set_name not in self.set_params.keys():
                            self.set_params[set_name] = count
        except Exception as e:
            print("error"+str(e))

    def convert_string_key_to_tuple(self):
        new_data = {}
        keys_replaced = []
        for key, value in self.name_params.items():
            try:
                if isinstance(key, str):
                    keys = key.split("~")
                    index = int(keys[0])
                    name = keys[1]
                    indexed_name = self.get_indexed_name(name, index)
                    new_data[indexed_name] = value
                    keys_replaced.append(key)
            except Exception as e:
                print("error "+str(e))
        for key in keys_replaced:
            self.name_params.pop(key)
        self.name_params.update(new_data)

    def remove_mqtt_and_datalist(self, v1):
        if isinstance(v1, dict):
            if "mqtt" in v1.keys():
                return {}
            elif "datalist" in v1.keys():
                return []
            else:
                for k2 in v1.keys():
                    v1[k2] = self.remove_mqtt_and_datalist(v1[k2])
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

    def extract_meta_values(self):
        meta_values = {}
        for name, params in self.name_params.items():
            if isinstance(name, str):

                pass
            else:
                index = name[1]
                for key, value in params.items():
                    if key not in ["mqtt", "datalist"]:
                        indexed_name = self.get_indexed_name(key, index)
                        meta_values[indexed_name] = value
        return meta_values

    def convert_name_params_to_model_params(self):
        name_model_params = {}
        for params in [self.name_params, self.meta_values]:
            for key in params.keys():
                if isinstance(key, str):
                    name_model_params[key] = 1
                else:
                    name = key[0]
                    if name not in name_model_params.keys():
                        name_model_params[name] = 1
                    else:
                        name_model_params[name] = name_model_params[name] + 1
        return name_model_params

    def check_keys_for_completeness(self):
        not_available_keys = []
        name_model_params = self.convert_name_params_to_model_params()
        all_keys = []
        all_keys.extend(self.optimization_params.keys())
        all_keys.extend(self.set_params.keys())
        for key, value in self.model_variables.items():
            if key not in self.derived:
                if value["type"] == "Set":
                    if key not in all_keys:
                        not_available_keys.append(key)
                elif value["type"] == "Param":
                    if key not in name_model_params.keys() and key not in all_keys:
                        not_available_keys.append(key)
                    elif key in name_model_params.keys():
                        indexing = value["indexing"]
                        if (len(indexing) == 1 and indexing[0] != "T" and indexing[0] in self.set_params.keys()
                                and self.set_params[indexing[0]] != name_model_params[key]) or \
                            (len(indexing) == 2 and indexing[1] in self.set_params.keys()
                                and self.set_params[indexing[1]] != name_model_params[key]):
                            not_available_keys.append(key)
        for key in self.base:
            if key not in all_keys and key not in name_model_params.keys():
                not_available_keys.append(key)
        return not_available_keys

    def add_meta_values_to_opt_params(self):
        new_data = {}
        for key, value in self.meta_values.items():
            name = key[0]
            index = key[1]
            indexing = self.get_variable_index(name)
            if len(indexing) > 0:
                if name in new_data.keys():
                    new_data[name].update({int(index): value})
                else:
                    new_data[name] = {int(index):value}
            else:
                new_data[name] = {None: value}
        self.optimization_params.update(new_data)


    def get_restart_value(self):
        return self.restart

    def get_forecast_flag(self, topic):
        if topic in self.name_params.keys() and "mqtt" in self.name_params[topic]:
            return True
        else:
            return False

    def get_generic_data_names(self):
        return self.generic_names

    def get_prediction_names(self):
        return self.prediction_names

    def get_pv_prediction_names(self):
        return self.pv_prediction_names

    def get_preprocess_names(self):
        return self.preprocess_names

    def get_event_names(self):
        return self.event_names

    def get_sampling_names(self):
        return self.sampling_names

    def get_variable_index(self, name):
        if not isinstance(name, str):
            name = name[0]
        if name in self.model_variables:
            return self.model_variables[name]["indexing"]
        else:
            return []

    def get_index_set_length(self, name):
        indexing = self.get_variable_index(name)
        if len(indexing) == 2:
            set_name = indexing[0]
            if set_name in self.set_params.keys():
                set_length = self.set_params[set_name]
                return set_name, set_length
            else:
                raise KeyError(set_name + " not in set params")
        return None, None

    def get_params(self, topic):
        return self.name_params[topic]["mqtt"]

    def get_optimization_values(self):
        return self.optimization_params

    def get_set_params(self):
        return self.set_params

    def get_meta_values(self):
        return self.meta_values