"""
Created on Aug 03 14:22 2018

@author: nishit
"""
import logging

import os

from IO.ConfigParserUtils import ConfigParserUtils
from IO.constants import Constants
from optimization.ModelParamsInfo import ModelParamsInfo
from profev.Car import Car
from profev.ChargingStation import ChargingStation
from profev.CarPark import CarPark

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


def generate_charger_classes(chargers):
    chargers_list = []
    for charger_name, charger_detail in chargers.items():
        max_charging_power_kw = charger_detail.get("Max_Charging_Power_kW", None)
        hosted_car = charger_detail.get("Hosted_Car", None)
        soc = charger_detail.get("SoC", None)
        assert max_charging_power_kw, f"Incorrect input: Max_Charging_Power_kW missing for charger: {charger_name}"
        chargers_list.append(ChargingStation(max_charging_power_kw, hosted_car, soc))
    return chargers_list


def generate_car_classes(cars):
    cars_list = []
    for car_name, car_detail in cars.items():
        battery_capacity = car_detail.get("Battery_Capacity_kWh", None)
        assert battery_capacity, f"Incorrect input: Battery_Capacity_kWh missing for car: {car_name}"
        cars_list.append(Car(car_name, battery_capacity))
    return cars_list


class InputConfigParser:

    def __init__(self, input_config_file, input_config_mqtt, model_name):
        self.model_name = model_name
        self.model_variables, self.param_key_list = ModelParamsInfo.get_model_param(self.model_name)
        self.input_config_file = input_config_file
        self.input_config_mqtt = input_config_mqtt
        self.mqtt_params = {}
        self.generic_names = []
        self.generic_file_names = []
        # self.defined_prediction_names = ["P_Load", "P_Load_R", "P_Load_S", "P_Load_T", "Q_Load_R", "Q_Load_S", "Q_Load_T", "Q_Load"]
        self.defined_prediction_names = []
        self.defined_non_prediction_names = ["P_PV"]
        self.defined_external_names = ["SoC_Value"]
        self.prediction_names = []
        self.non_prediction_names = []
        self.external_names = []
        self.config_parser_utils = ConfigParserUtils()
        self.extract_mqtt_params()
        self.car_park = None
        self.optimization_params = self.extract_optimization_values()
        logger.debug("optimization_params: " + str(self.optimization_params))
        logger.info("generic names = " + str(self.generic_names))

    def read_predict_flag(self, value2, name):
        if isinstance(value2, dict):
            if "predict" in value2.keys():
                predict = bool(value2["predict"])
                if predict:
                    self.defined_prediction_names.append(name)

    def extract_mqtt_params(self):
        for key, value in self.input_config_mqtt.items():
            for key2, value2 in value.items():
                mqtt = self.config_parser_utils.get_mqtt(value2)
                self.read_predict_flag(value2, key2)
                if mqtt is not None:
                    self.mqtt_params[key2] = mqtt.copy()
                    self.add_name_to_list(key2)
        logger.info("params = " + str(self.mqtt_params))

    def add_name_to_list(self, key):
        if key in self.defined_prediction_names:
            self.prediction_names.append(key)
        elif key in self.defined_non_prediction_names:
            self.non_prediction_names.append(key)
        elif key in self.defined_external_names:
            self.external_names.append(key)
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
                                try:
                                    v2 = float(v2)
                                except ValueError:
                                    pass
                                if isinstance(v2, float) and v2.is_integer():
                                    v2 = int(v2)
                                if k2 in self.model_variables.keys():
                                    indexing = self.model_variables[k2]["indexing"]
                                    if indexing == "index":
                                        data[k2] = {int(0): v2}
                                    elif indexing == "None":
                                        data[k2] = {None: v2}
                                else:
                                    data[k2] = {None: v2}
                        elif k1 == Constants.SoC_Value and isinstance(v1, int):
                            indexing = self.model_variables[Constants.SoC_Value]["indexing"]
                            if indexing == "index":
                                data[Constants.SoC_Value] = {int(0): float(v1 / 100)}
                            elif indexing == "None":
                                data[Constants.SoC_Value] = {None: float(v1 / 100)}
                        elif isinstance(v1, list):
                            self.add_name_to_list(k1)
                        elif k == "generic" and not isinstance(v1, dict):
                            logger.debug("Generic single value")
                            try:
                                v1 = float(v1)
                            except ValueError:
                                pass
                            if isinstance(v1, float) and v1.is_integer():
                                v1 = int(v1)
                            data[k1] = {None: v1}
                        elif k == "PROFEV":
                            if isinstance(v1, dict):
                                if k1 == Constants.CarPark:
                                    chargers = v1.get("Charging_Station", None)
                                    cars = v1.get("Cars", None)
                                    assert chargers, "Incorrect input: Charging_Station missing in CarPark"
                                    assert cars, "Incorrect input: Cars missing in CarPark"
                                    chargers = dict(chargers)
                                    cars = dict(cars)
                                    chargers_list = generate_charger_classes(chargers)
                                    cars_list = generate_car_classes(cars)
                                    self.car_park = CarPark(chargers_list, cars_list)

                                    data["Number_of_Parked_Cars"] = {None: self.car_park.number_of_cars}
                                    data["VAC_Capacity"] = {None: self.car_park.vac_capacity}

                                if k1 == Constants.Uncertainty:
                                    data["Value"] = "null"
                                    data["Initial_ESS_SoC"] = "null"
                                    data["Initial_VAC_SoC"] = "null"
                                    data["Behavior_Model"] = "null"
                                    pass
                            else:
                                try:
                                    v1 = float(v1)
                                except:
                                    pass
                                if isinstance(v1, float) and v1.is_integer():
                                    v1 = int(v1)
                                data[k1] = {None: v1}
        return data

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

    def get_variable_index(self, name):
        if name in self.model_variables:
            return self.model_variables[name]["indexing"]
        else:
            return None

    def get_params(self, topic):
        return self.mqtt_params[topic]

    def get_optimization_values(self):
        return self.optimization_params

    def check_keys_for_completeness(self):
        all_keys = []
        all_keys.extend(self.prediction_names)
        all_keys.extend(self.non_prediction_names)
        all_keys.extend(self.external_names)
        all_keys.extend(self.generic_names)
        all_keys.extend(self.optimization_params.keys())
        all_keys.append("dT")

        not_available_keys = []
        for key in self.param_key_list:
            if key not in all_keys:
                not_available_keys.append(key)
        return not_available_keys
