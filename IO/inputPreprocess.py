"""
Created on Mai 21 14:08 2019

@author: nishit
"""
import json
import os
from functools import partial

import numpy as np

from profev.EVPark import EVPark
from profev.MonteCarloSimulator import simulate
from utils_intern.constants import Constants

from utils_intern.messageLogger import MessageLogger


class InputPreprocess:

    def __init__(self, id, mqtt_time_threshold, config, name_params, initial_opt_values):
        self.data_dict = {}
        self.name_params = name_params
        self.initial_opt_values = initial_opt_values
        self.initial_pass = False
        self.logger = MessageLogger.get_logger(__name__, id)
        persist_real_data_path = "optimization/resources"
        persist_real_data_path = os.path.join("/usr/src/app", persist_real_data_path, id, "real")
        # persist_real_data_path = os.path.join(os.getcwd())
        self.persist_real_data_file = os.path.join(persist_real_data_path, "ev_info" + ".txt")
        self.ev_park = EVPark(id, self.persist_real_data_file)
        self.id = id
        self.mqtt_time_threshold = mqtt_time_threshold
        self.event_data = []
        self.charger_unplug_event = []
        persist_base_file_path = config.get("IO", "persist.base.file.path")
        self.charger_base_path = os.path.join("/usr/src/app", persist_base_file_path, str(id),
                                              Constants.persisted_folder_name)
        self.charger_file_name = "chargers.json"
        self.create_ev_and_charger_classes()
        self.process_initial_uncertainty_data()

    def create_ev_and_charger_classes(self):
        ev_data_from_file = None
        if os.path.exists(self.persist_real_data_file):
            ev_data_from_file = self.read_data(self.persist_real_data_file)
            self.logger.debug("Data from file read: " + str(self.persist_real_data_file))

        for k, v in self.name_params.items():
            name = k[0]
            if self.is_ev(v):
                ev = name
                ev_dict = v
                battery_capacity = ev_dict.get("Battery_Capacity_kWh", None)
                assert battery_capacity, "Incorrect input: Battery_Capacity_kWh missing for EV: " + str(ev)
                soc = None
                if ev_data_from_file is not None:
                    if ev in ev_data_from_file.keys():
                        soc = ev_data_from_file[ev]
                self.logger.debug("soc " + str(soc) + " ev_no_base " + str(ev))
                self.ev_park.add_ev(ev, battery_capacity, soc)
            elif self.is_charger(v):
                charger = name
                charger_dict = v
                max_charging_power_kw = charger_dict.get("Max_Charging_Power_kW", None)
                hosted_ev = charger_dict.get("Hosted_EV", None)

                # setting hosted ev to none now, bcoz the actual recharge event would be processed later,
                # but we don't want to unplug ev from another charger if this charger is going to be unplugged
                if charger in self.charger_unplug_event:
                    hosted_ev = None

                self.logger.debug("hosted_ev " + str(hosted_ev))
                self.ev_park.add_charger(charger, max_charging_power_kw, hosted_ev, None)

    def event_received(self, data):
        self.logger.info("event received = " + str(data))
        for key, value in data.items():
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, list):
                        timestamp = v[0]
                        event = v[1]
                        if isinstance(event, dict):
                            for charger_name, charger_value in event.items():
                                if "recharge" in key and isinstance(charger_value, dict) and "recharge" in charger_value.keys():
                                    recharge_state = charger_value["recharge"]
                                    hosted_ev = None
                                    if "Hosted_EV" in charger_value.keys():
                                        hosted_ev = charger_value["Hosted_EV"]
                                    self.logger.debug(
                                        "recharge_state " + str(recharge_state) + " for hosted ev " + str(
                                            hosted_ev) + " in charger " + str(charger_name))

                                    self.event_data.append([charger_name, recharge_state, timestamp, hosted_ev])
                                    if recharge_state == Constants.recharge_event_disconnect:
                                        self.charger_unplug_event.append(charger_name)

    def process_events(self):
        self.logger.info("events to be processed = " + str(self.event_data))
        for charger_name, recharge_state, timestamp, hosted_ev in self.event_data:
            self.ev_park.add_recharge_event(charger_name, recharge_state, timestamp, hosted_ev)
            self.logger.debug("ev_park chargers[charger_name] " + str(
                self.ev_park.chargers[charger_name]))
        self.logger.info("events to be considered later = " + str(self.event_data))
        self.event_data = []
        self.charger_unplug_event = []

    def preprocess(self, data_dict, mqtt_timer):
        self.logger.info("data_dict = " + str(data_dict))
        self.data_dict = data_dict
        self.last_timesamps = mqtt_timer
        self.logger.info("mqtt timer = " + str(mqtt_timer))

        """Read and process data from data dictionary"""
        """Process data dict data to build ev park"""
        self.update_charger_classes()
        self.ev_park.set_ev_soc()

        """process the recharge event. if we have soc and recharge = 1 (unplug) then it would be unplug-ed"""
        self.process_events()

        """get processed data"""
        number_of_evs, vac_capacity = self.ev_park.get_num_of_cars(), self.ev_park.get_vac_capacity()
        recharge = self.ev_park.single_ev_recharge()
        self.logger.info("Recharge value: " + str(recharge))

        soc_value, vac_soc_value = self.process_uncertainty_data()

        """Set the data in data dictionary"""
        self.set_data_in_data_dict(number_of_evs, vac_capacity, soc_value, vac_soc_value, recharge)

        for charger_id, charger in self.ev_park.chargers.items():
            self.logger.info(charger.__str__())

        self.persist_charger_data()

        # time.sleep(60)
        self.logger.info("data_dict = " + str(self.data_dict))
        return self.data_dict

    def set_data_in_data_dict(self, number_of_evs, vac_capacity, soc_value, vac_soc_value, recharge):
        self.data_dict["Number_of_Parked_Cars"] = {None: number_of_evs}  # Total no. of cars
        self.data_dict["VAC_Capacity"] = {None: vac_capacity}
        self.data_dict["SoC_Value"] = {None: soc_value}
        self.data_dict["VAC_SoC_Value"] = {None: vac_soc_value}
        self.data_dict["Recharge"] = {None: recharge}

        self.data_dict["VAC_States_Min"] = {None: self.vac_min}

        self.data_dict["Value"] = "null"
        self.data_dict["Initial_ESS_SoC"] = "null"
        self.data_dict["Initial_VAC_SoC"] = "null"
        self.data_dict["Behavior_Model"] = "null"

    def get_last_timestamp(self, partial_key):
        timestamp = -1
        for k, v in self.last_timesamps.items():
            if partial_key in k:
                timestamp = v
                break
        return timestamp

    def remove_key_base(self, key):
        i = key.rfind("/")
        if i > 0:
            return key[i + 1:]
        else:
            return key

    def get_key_base(self, key):
        i = key.find("/")
        if i > 0:
            return key[:i]
        else:
            return key

    def get_name_param_value(self, key):
        for k, v in self.name_params.items():
            if key == k[0]:
                return v
        return None

    def is_charger(self, data):
        if data is not None and isinstance(data, dict):
            if "Max_Charging_Power_kW" in data.keys():
                return True
        return False

    def is_ev(self, data):
        if data is not None and isinstance(data, dict):
            if "Battery_Capacity_kWh" in data.keys():
                return True
        return False

    def update_charger_classes(self):
        charger_time = []
        charger_keys = []
        for k, v in self.data_dict.items():
            charger = self.get_key_base(k)
            if charger in self.ev_park.chargers.keys():
                last_timestamp = self.get_last_timestamp(k)
                charger_time.append([k, last_timestamp])
                charger_keys.append(k)

        # sort so the newest data get most preference
        charger_time.sort(key=lambda x: x[1])
        for k, last_timestamp in charger_time:
            charger = self.get_key_base(k)
            key = self.remove_key_base(k)  # soc or hosted ev
            values = self.data_dict[k]

            self.logger.debug("charger " + str(charger) + " last timestamp: " + str(last_timestamp))
            if key == "SoC":
                value = None
                for i, v in values.items():
                    value = v

                soc = None
                hosted_ev = None
                if isinstance(value, dict):
                    for attr, v in value.items():
                        if attr == "SoC":
                            soc = v
                        elif attr == "Hosted_EV":
                            hosted_ev = v
                elif isinstance(value, int) or isinstance(value, float):
                    soc = value

                self.logger.debug("charger " + str(charger) + "key " + str(key)+ " value " + str(value))
                self.ev_park.update_charger_for_key(charger, soc, hosted_ev)

    def read_data(self, filepath):
        try:
            with open(filepath, "r") as file:
                data = file.read()
            return json.loads(data)
        except Exception as e:
            self.logger.error("Read input file exception: " + str(e))

    def process_initial_uncertainty_data(self):
        monte_carlo_repetition = None
        if "monte_carlo_repetition" in self.initial_opt_values.keys():
            monte_carlo_repetition = self.initial_opt_values["monte_carlo_repetition"][None]

        # TODO: assumption that only one plugged_time_key
        plugged_time = self.get_name_param_value("Plugged_Time")
        unplugged_time = self.get_name_param_value("Unplugged_Time")
        assert plugged_time, "Plugged_Time is missing in Uncertainty"
        assert unplugged_time, "Unplugged_Time is missing in Uncertainty"
        assert monte_carlo_repetition, "monte_carlo_repetition is missing in Uncertainty"

        plugged_time_mean = plugged_time.get("mean", None)
        plugged_time_std = plugged_time.get("std", None)
        unplugged_time_mean = unplugged_time.get("mean", None)
        unplugged_time_std = unplugged_time.get("std", None)
        assert plugged_time_mean, "mean value missing in Plugged_Time"
        assert plugged_time_std, "std value missing in Plugged_Time"
        assert unplugged_time_mean, "mean value missing in Unlugged_Time"
        assert unplugged_time_std, "std value missing in Unlugged_Time"

        self.simulator = partial(simulate,
                                 repetition=monte_carlo_repetition,
                                 unplugged_mean=unplugged_time_mean, unplugged_std=unplugged_time_std,
                                 plugged_mean=plugged_time_mean, plugged_std=plugged_time_std)

        # TODO: assumption that only one key
        ess_states = self.get_name_param_value("ESS_States")
        vac_states = self.get_name_param_value("VAC_States")
        assert ess_states, "ESS_States is missing in Uncertainty"
        assert vac_states, "VAC_States is missing in Uncertainty"

        # Crucial to set them to self as they are being read in optimization
        self.ess_min, ess_max, self.ess_steps, self.ess_soc_states = self.generate_states(ess_states, "ESS_States")
        self.logger.debug("ess_soc_states " + str(self.ess_soc_states))
        self.vac_min, vac_max, self.vac_steps, self.vac_soc_states = self.generate_states(vac_states, "VAC_States")
        self.logger.debug("vac_soc_states " + str(self.vac_soc_states))

        self.VAC_SoC_Value_override = None
        if "VAC_SoC_Value_override" in self.initial_opt_values.keys():
            self.VAC_SoC_Value_override = self.initial_opt_values["VAC_SoC_Value_override"][None]

        if "Unit_Consumption_Assumption" in self.initial_opt_values.keys():
            uac = float(self.initial_opt_values["Unit_Consumption_Assumption"][None])
            if not (((uac - self.vac_min) / self.vac_steps).is_integer()):
                raise Exception("Unit_Consumption_Assumption should be a valid step of VAC_steps")
        else:
            raise Exception("Unit_Consumption_Assumption missing")

    def process_uncertainty_data(self):
        vac_soc_value = self.ev_park.calculate_vac_soc_value(vac_soc_value_override=self.VAC_SoC_Value_override)
        vac_soc_value = self.round_to_steps(vac_soc_value, self.vac_min, self.vac_steps)

        soc_value = None
        for key, value in self.data_dict["SoC_Value"].items():
            if isinstance(value, dict):
                self.logger.debug("multiple soc")
            else:
                soc_value = value
                break

        if soc_value:
            soc_value = self.round_to_steps(soc_value, self.ess_min, self.ess_steps)
            if soc_value < self.ess_min:
                soc_value = self.ess_min

        if vac_soc_value < self.vac_min:
            vac_soc_value = self.vac_min

        self.logger.info("vac_soc_value = " + str(vac_soc_value))
        self.logger.info("soc_value = " + str(soc_value))

        return soc_value, vac_soc_value

    def generate_states(self, states, state_name):
        self.logger.debug("states " + str(states))
        min_value = states.get("Min", None)
        max_value = states.get("Max", None)
        steps = states.get("Steps", None)

        assert min_value!=None, "Min value missing in " + str(state_name)
        assert max_value, "Max value missing in " + str(state_name)
        assert steps, "Steps value missing in " + str(state_name)

        return (min_value, max_value, steps, np.arange(min_value, max_value + steps, steps).tolist())

    def round_to_steps(self, value, min, step):
        self.logger.info("round values " + str(value) + " " + str(min) + " " + str(step))
        return round((value - min) / step) * step + min

    def persist_charger_data(self):
        try:
            if not os.path.exists(self.charger_base_path):
                os.makedirs(self.charger_base_path)
            file_path = os.path.join(self.charger_base_path, self.charger_file_name)
            with open(file_path, "w") as f:
                data = self.ev_park.get_chargers_dict_list()
                if len(data) > 0:
                    json_data = json.dumps(data)
                    f.write(json_data)
                    self.logger.debug("charger data persisted " + file_path)
                    # print("charger data persisted "+file_path)
        except Exception as e:
            self.logger.error("error persisting charger data " + str(e))
