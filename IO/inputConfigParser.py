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
from profev.Car import Car
from profev.ChargingStation import ChargingStation
from profev.CarPark import CarPark
from profev.MonteCarloSimulator import simulate

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
        self.set_params = {}
        self.config_parser_utils = ConfigParserUtils()
        self.extract_mqtt_params()
        self.car_park = None
        self.simulator = None
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

    def generate_car_park(self, details):
        chargers = details.get("Charging_Station", None)
        cars = details.get("Cars", None)
        assert chargers, "Incorrect input: Charging_Station missing in CarPark"
        assert cars, "Incorrect input: Cars missing in CarPark"
        chargers = dict(chargers)
        cars = dict(cars)
        chargers_list = generate_charger_classes(chargers)
        cars_list = generate_car_classes(cars)
        self.car_park = CarPark(chargers_list, cars_list)

        return self.car_park.number_of_cars, self.car_park.vac_capacity

    def generate_behaviour_model(self, plugged_time, unplugged_time, simulation_repetition):
        plugged_time_mean = plugged_time.get("mean", None)
        plugged_time_std = plugged_time.get("std", None)

        assert plugged_time_mean, "mean value missing in Plugged_Time"
        assert plugged_time_std, "std value missing in Plugged_Time"

        unplugged_time_mean = plugged_time.get("mean", None)
        unplugged_time_std = plugged_time.get("std", None)

        assert unplugged_time_mean, "mean value missing in Unlugged_Time"
        assert unplugged_time_std, "std value missing in Unlugged_Time"

        self.simulator = partial(simulate,
                                 repetition=simulation_repetition,
                                 unplugged_mean=unplugged_time_mean, unplugged_std=unplugged_time_std,
                                 plugged_mean=plugged_time_mean, plugged_std=plugged_time_std)

    def generate_states(self, states, state_name):
        min_value = states.get("Min", None)
        max_value = states.get("Max", None)
        steps = states.get("Steps", None)

        assert min_value != None, f"Min value missing in {state_name}"
        assert max_value, f"Max value missing in {state_name}"
        assert steps, f"Steps value missing in {state_name}"

        min_value = int(min_value)
        max_value = int(max_value)

        return min_value, max_value, steps, np.arange(min_value, max_value + steps, steps).tolist()

    def extract_optimization_values(self):
        data = {}
        for input_config in [self.input_config_file, self.input_config_mqtt]:
            for k, v in input_config.items():
                if isinstance(v, dict):
                    for k1, v1 in v.items():
                        if k1 == Constants.meta:
                            for k2, v2 in v1.items():
                                self.add_value_to_data(data, k2, v2)
                        elif k1 == Constants.SoC_Value:
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
                            logger.debug("Generic single value")
                            self.add_value_to_data(data, k1, v1)
                        elif k == "PROFEV":
                            if isinstance(v1, dict):
                                if k1 == Constants.CarPark:
                                    number_of_cars, vac_capacity = self.generate_car_park(v1)

                                    data["Number_of_Parked_Cars"] = {None: number_of_cars}
                                    data["VAC_Capacity"] = {None: vac_capacity}

                                if k1 == Constants.Uncertainty:
                                    plugged_time = v1.get("Plugged_Time", None)
                                    unplugged_time = v1.get("Unplugged_Time", None)
                                    simulation_repetition = v1.get("simulation_repetition", None)

                                    assert plugged_time, "Plugged_Time is missing in Uncertainty"
                                    assert unplugged_time, "Unplugged_Time is missing in Uncertainty"
                                    assert simulation_repetition, "simulation_repetition is missing in Uncertainty"

                                    self.generate_behaviour_model(plugged_time, unplugged_time, simulation_repetition)

                                    ess_states = v1.get("ESS_States", None)
                                    vac_states = v1.get("VAC_States", None)

                                    assert ess_states, "ESS_States is missing in Uncertainty"
                                    assert vac_states, "VAC_States is missing in Uncertainty"

                                    _, _, ess_steps, ess_soc_states = self.generate_states(ess_states, "ESS_States")
                                    _, _, vac_steps, vac_soc_states = self.generate_states(vac_states, "VAC_States")

                                    self.ess_steps = ess_steps
                                    self.vac_steps = vac_steps
                                    self.ess_soc_states = ess_soc_states
                                    self.vac_soc_states = vac_soc_states

                                    data["Value"] = "null"
                                    data["Initial_ESS_SoC"] = "null"
                                    data["Initial_VAC_SoC"] = "null"
                                    data["Behavior_Model"] = "null"
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
        all_keys.extend(self.optimization_params.keys())
        all_keys.extend(self.set_params.keys())
        all_keys.append("dT")
        all_keys.append("T")
        logger.info("model_variables : "+ str(self.model_variables))
        logger.info("all_keys : " + str(all_keys))
        not_available_keys = []
        for key in self.model_variables.keys():
            if key not in all_keys and self.model_variables[key]["type"] in ["Set", "Param"]:
                not_available_keys.append(key)
        return not_available_keys
