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

    def __init__(self, id, mqtt_time_threshold, config):
        self.data_dict = {}
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
        self.generate_ev_classes()
        self.generate_charger_classes()
        self.ev_park.set_ev_soc()

        """process the recharge event. if we have soc and recharge = 1 (unplug) then it would be unplug-ed"""
        self.process_events()

        """get processed data"""
        number_of_evs, vac_capacity = self.ev_park.get_num_of_cars(), self.ev_park.get_vac_capacity()
        recharge = self.ev_park.single_ev_recharge()
        self.logger.info("Recharge value: " + str(recharge))

        if not self.initial_pass:
            self.process_initial_uncertainty_data()
        self.generate_behaviour_model()
        soc_value, vac_soc_value = self.process_uncertainty_data()

        """Set the data in data dictionary"""
        self.set_data_in_data_dict(number_of_evs, vac_capacity, soc_value, vac_soc_value, recharge)

        for charger_id, charger in self.ev_park.chargers.items():
            self.logger.info(charger.__str__())

        self.persist_charger_data()

        if not self.initial_pass:
            self.initial_pass = True
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

    def validate_unit_consumption_assumption(self, vac_min, vac_step):
        self.logger.info("data_dict : " + str(self.data_dict))
        if "Unit_Consumption_Assumption" in self.data_dict.keys():
            uac = float(self.data_dict["Unit_Consumption_Assumption"][None])
            self.logger.debug(
                "Unit consumption assumption " + str(uac) + " vac_min " + str(vac_min) + " vac_step " + str(vac_step))
            if not (((uac - vac_min) / vac_step).is_integer()):
                raise Exception("Unit_Consumption_Assumption should be a valid step of VAC_steps")
        else:
            raise Exception("Unit_Consumption_Assumption missing")

    def remove_key_base(self, key):
        i = key.rfind("/")
        if i > 0:
            return key[i + 1:]
        else:
            return key

    def get_required_keys(self, partial_key):
        keys = []
        for k in self.data_dict.keys():
            if partial_key in k:
                keys.append(k)
        return keys

    def remove_used_keys(self, keys):
        for k in keys:
            self.data_dict.pop(k)
        return keys

    def is_charger(self, data):
        if data is not None and isinstance(data, dict):
            if "Max_Charging_Power_kW" in data.keys() or "Hosted_EV" in data.keys():
                return True
        return False

    def is_ev(self, data):
        if data is not None and isinstance(data, dict):
            if "Battery_Capacity_kWh" in data.keys():
                return True
        return False

    def generate_charger_classes(self):
        charger_keys = []
        charger_time = []
        for k, v in self.data_dict.items():
            if self.is_charger(v):
                last_timestamp = self.get_last_timestamp(k)
                charger_time.append([k, last_timestamp])
                charger_keys.append(k)

        # sort so the newest data get most preference
        charger_time.sort(key = lambda x:x[1])
        for charger_id, last_timestamp in charger_time:
            charger_dict = self.data_dict[charger_id]

            self.logger.info("charger " + str(charger_id) + " last timestamp: " + str(last_timestamp))
            self.logger.info("charger dict " + str(charger_dict))

            max_charging_power_kw = charger_dict.get("Max_Charging_Power_kW", None)
            hosted_ev = charger_dict.get("Hosted_EV", None)
            soc = charger_dict.get("SoC", None)
            ev_unplugged = False

            if not (isinstance(soc, float) or isinstance(soc, int)):
                soc = None
                ev_unplugged = True

            # setting hosted ev to none now, bcoz the actual recharge event would be processed later,
            # but we don't want to unplug ev from another charger if this charger is going to be unplugged
            if charger_id in self.charger_unplug_event:
                hosted_ev = None

            self.logger.debug(
                "hosted_ev " + str(hosted_ev) + " with soc " + str(soc) + " ev_unplugged " + str(ev_unplugged))
            self.ev_park.add_charger(charger_id, max_charging_power_kw, hosted_ev, soc)

        self.remove_used_keys(charger_keys)

    def generate_ev_classes(self):
        ev_data_from_file = None
        if os.path.exists(self.persist_real_data_file):
            ev_data_from_file = self.read_data(self.persist_real_data_file)
            self.logger.debug("Data from file read: " + str(self.persist_real_data_file))

        ev_keys = []
        for k, v in self.data_dict.items():
            if self.is_ev(v):
                ev = k
                ev_dict = v
                ev_keys.append(k)
                battery_capacity = ev_dict.get("Battery_Capacity_kWh", None)
                assert battery_capacity, "Incorrect input: Battery_Capacity_kWh missing for EV: " + str(ev)
                self.logger.debug("ev " + str(ev))
                ev_no_base = self.remove_key_base(ev)
                soc = None
                if ev_data_from_file is not None:
                    if ev in ev_data_from_file.keys():
                        soc = ev_data_from_file[ev]
                self.logger.debug("soc " + str(soc) + " ev_no_base " + str(ev_no_base))
                self.ev_park.add_ev(ev_no_base, battery_capacity, soc)
        #self.remove_used_keys(ev_keys)

    def read_data(self, filepath):
        try:
            with open(filepath, "r") as file:
                data = file.read()
            return json.loads(data)
        except Exception as e:
            self.logger.error("Read input file exception: " + str(e))

    def process_initial_uncertainty_data(self):
        plugged_time_key = self.get_required_keys("Plugged_Time")
        unplugged_time_key = self.get_required_keys("Unplugged_Time")
        monte_carlo_repetition_key = self.get_required_keys("monte_carlo_repetition")
        self.plugged_time, self.unplugged_time, self.monte_carlo_repetition = None, None, None
        # TODO: assumption that only one plugged_time_key
        if len(plugged_time_key) > 0:
            plugged_time = self.data_dict.get(plugged_time_key[0], None)
        if len(unplugged_time_key) > 0:
            unplugged_time = self.data_dict.get(unplugged_time_key[0], None)
        if len(monte_carlo_repetition_key) > 0:
            self.monte_carlo_repetition = self.data_dict.get(monte_carlo_repetition_key[0], None)
            if isinstance(self.monte_carlo_repetition, dict):
                val = None
                for k, v in self.monte_carlo_repetition.items():
                    val = v
                self.monte_carlo_repetition = val

        assert plugged_time, "Plugged_Time is missing in Uncertainty"
        assert unplugged_time, "Unplugged_Time is missing in Uncertainty"
        assert self.monte_carlo_repetition, "monte_carlo_repetition is missing in Uncertainty"

        self.plugged_time_mean = plugged_time.get("mean", None)
        self.plugged_time_std = plugged_time.get("std", None)
        self.unplugged_time_mean = unplugged_time.get("mean", None)
        self.unplugged_time_std = unplugged_time.get("std", None)

        assert self.plugged_time_mean, "mean value missing in Plugged_Time"
        assert self.plugged_time_std, "std value missing in Plugged_Time"
        assert self.unplugged_time_mean, "mean value missing in Unlugged_Time"
        assert self.unplugged_time_std, "std value missing in Unlugged_Time"

        ess_states_keys = self.get_required_keys("ESS_States")
        vac_states_keys = self.get_required_keys("VAC_States")

        ess_states, vac_states = None, None
        # TODO: assumption that only one key
        if len(ess_states_keys) > 0:
            ess_states = self.data_dict.get(ess_states_keys[0], None)
        if len(vac_states_keys) > 0:
            vac_states = self.data_dict.get(vac_states_keys[0], None)

        assert ess_states, "ESS_States is missing in Uncertainty"
        assert vac_states, "VAC_States is missing in Uncertainty"

        # Crucial to set them to self as they are being read in optimization
        self.ess_min, ess_max, self.ess_steps, self.ess_soc_states = self.generate_states(ess_states, "ESS_States")
        self.logger.debug("ess_soc_states " + str(self.ess_soc_states))
        self.vac_min, vac_max, self.vac_steps, self.vac_soc_states = self.generate_states(vac_states, "VAC_States")
        self.logger.debug("vac_soc_states " + str(self.vac_soc_states))

        self.remove_used_keys(plugged_time_key)
        self.remove_used_keys(unplugged_time_key)
        self.remove_used_keys(ess_states_keys)
        self.remove_used_keys(vac_states_keys)

    def generate_behaviour_model(self):
        self.simulator = partial(simulate,
                                 repetition=self.monte_carlo_repetition,
                                 unplugged_mean=self.unplugged_time_mean, unplugged_std=self.unplugged_time_std,
                                 plugged_mean=self.plugged_time_mean, plugged_std=self.plugged_time_std)

    def process_uncertainty_data(self):
        VAC_SoC_Value_override = None
        if "VAC_SoC_Value_override" in self.data_dict.keys():
            VAC_SoC_Value_override = self.data_dict["VAC_SoC_Value_override"][None]
        vac_soc_value = self.ev_park.calculate_vac_soc_value(vac_soc_value_override=VAC_SoC_Value_override)
        vac_soc_value = self.round_to_steps(vac_soc_value, self.vac_min, self.vac_steps)

        soc_value_key = None
        for key, value in self.data_dict["SoC_Value"].items():
            soc_value_key = key
            break

        soc_value = self.data_dict["SoC_Value"][soc_value_key]
        soc_value = self.round_to_steps(soc_value, self.ess_min, self.ess_steps)

        if vac_soc_value < self.vac_min:
            vac_soc_value = self.vac_min

        if soc_value < self.ess_min:
            soc_value = self.ess_min

        self.validate_unit_consumption_assumption(self.vac_min, self.vac_steps)

        self.logger.info("vac_soc_value = " + str(vac_soc_value))
        self.logger.info("soc_value = " + str(soc_value))

        return soc_value, vac_soc_value

    def generate_states(self, states, state_name):
        self.logger.debug("states " + str(states))
        min_value = states.get("Min", None)
        max_value = states.get("Max", None)
        steps = states.get("Steps", None)

        assert min_value != None, "Min value missing in " + str(state_name)
        assert max_value, "Max value missing in " + str(state_name)
        assert steps, "Steps value missing in " + str(state_name)

        # min_value = int(min_value)
        # max_value = int(max_value)

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
