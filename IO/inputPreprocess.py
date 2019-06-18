"""
Created on Mai 21 14:08 2019

@author: nishit
"""
import logging
from functools import partial

import numpy as np
import time

from profev.EV import EV
from profev.EVPark import EVPark
from profev.ChargingStation import ChargingStation
from profev.MonteCarloSimulator import simulate
from utils_intern.messageLogger import MessageLogger

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class InputPreprocess:

    def __init__(self, id):
        self.data_dict = {}
        self.logger = self.logger = MessageLogger.get_logger(__file__, id)

    def preprocess(self, data_dict):
        self.logger.info("data_dict = "+str(data_dict))
        self.ev_park = EVPark()
        self.data_dict = {}
        self.data_dict = data_dict

        evs_list = self.generate_ev_classes()
        self.ev_park.add_evs(evs_list)
        chargers_list = self.generate_charger_classes()
        self.ev_park.add_chargers(chargers_list)
        number_of_evs, vac_capacity = self.ev_park.get_num_of_cars(), self.ev_park.get_vac_capacity()
        self.data_dict["Number_of_Parked_Cars"] = {None: number_of_evs}
        self.data_dict["VAC_Capacity"] = {None: vac_capacity}

        self.process_uncertainty_data()

        return self.data_dict

    def validate_unit_consumption_assumption(self, vac_min, vac_step):
        self.logger.info("data_dict : "+str(self.data_dict))
        if "Unit_Consumption_Assumption" in self.data_dict.keys():
            uac = self.data_dict["Unit_Consumption_Assumption"][None]
            if not (uac >= vac_min and ((uac - vac_min) / vac_step).is_integer()):
                raise Exception("Unit_Consumption_Assumption should be a valid step of VAC_steps and greater than "
                                "VAC_min")
        else:
            raise Exception("Unit_Consumption_Assumption missing")

    def remove_key_base(self, key):
        i = key.rfind("/")
        if i > 0:
            return key[i+1:]
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

    def generate_charger_classes(self):
        chargers_list = []
        chargers = self.get_required_keys("charger")
        for charger in chargers:
            charger_dict = self.data_dict[charger]
            self.logger.info("charger dict "+str(charger_dict))
            max_charging_power_kw = charger_dict.get("Max_Charging_Power_kW", None)
            hosted_ev = charger_dict.get("Hosted_EV", None)
            soc = charger_dict.get("SoC", None)
            if not (isinstance(soc, float) or isinstance(soc, int)):
                soc = None
            assert max_charging_power_kw, f"Incorrect input: Max_Charging_Power_kW missing for charger: {charger}"
            chargers_list.append(ChargingStation(charger, max_charging_power_kw, hosted_ev, soc))
        self.remove_used_keys(chargers)
        return chargers_list

    def generate_ev_classes(self):
        evs_list = []
        evs = self.get_required_keys("ev")
        for ev in evs:
            ev_dict = self.data_dict[ev]
            battery_capacity = ev_dict.get("Battery_Capacity_kWh", None)
            assert battery_capacity, f"Incorrect input: Battery_Capacity_kWh missing for EV: {ev}"
            ev_no_base = self.remove_key_base(ev)
            evs_list.append(EV(ev_no_base, battery_capacity))
        self.remove_used_keys(evs)
        return evs_list

    def process_uncertainty_data(self):
        plugged_time_key = self.get_required_keys("Plugged_Time")
        unplugged_time_key = self.get_required_keys("Unplugged_Time")
        monte_carlo_repetition_key = self.get_required_keys("monte_carlo_repetition")
        plugged_time, unplugged_time, monte_carlo_repetition = None, None, None
        # TODO: assumption that only one plugged_time_key
        if len(plugged_time_key) > 0:
            plugged_time = self.data_dict.get(plugged_time_key[0], None)
        if len(unplugged_time_key) > 0:
            unplugged_time = self.data_dict.get(unplugged_time_key[0], None)
        if len(monte_carlo_repetition_key) > 0:
            monte_carlo_repetition = self.data_dict.get(monte_carlo_repetition_key[0], None)
            if isinstance(monte_carlo_repetition, dict):
                val = None
                for k, v in monte_carlo_repetition.items():
                    val = v
                monte_carlo_repetition = val

        assert plugged_time, "Plugged_Time is missing in Uncertainty"
        assert unplugged_time, "Unplugged_Time is missing in Uncertainty"
        assert monte_carlo_repetition, "monte_carlo_repetition is missing in Uncertainty"

        self.generate_behaviour_model(plugged_time, unplugged_time, monte_carlo_repetition)

        self.remove_used_keys(plugged_time_key)
        self.remove_used_keys(unplugged_time_key)

        ess_states_keys = self.get_required_keys("ESS_States")
        vac_states_keys = self.get_required_keys("VAC_States")

        ess_states, vac_states = None, None
        # TODO: assumption that only one plugged_time_key
        if len(ess_states_keys) > 0:
            ess_states = self.data_dict.get(ess_states_keys[0], None)
        if len(vac_states_keys) > 0:
            vac_states = self.data_dict.get(vac_states_keys[0], None)

        assert ess_states, "ESS_States is missing in Uncertainty"
        assert vac_states, "VAC_States is missing in Uncertainty"

        _, _, ess_steps, ess_soc_states = self.generate_states(ess_states, "ESS_States")
        vac_min, vac_max, vac_steps, vac_soc_states = self.generate_states(vac_states, "VAC_States")

        self.ess_steps = ess_steps
        self.vac_steps = vac_steps
        self.ess_soc_states = ess_soc_states
        self.vac_soc_states = vac_soc_states

        vac_soc_value = self.ev_park.calculate_vac_soc_value()
        vac_soc_value = self.round_to_steps(vac_soc_value, vac_min, vac_steps)

        self.logger.info("vac_soc_value = "+str(vac_soc_value))

        self.data_dict["VAC_SoC_Value"] = {None: vac_soc_value}
        self.data_dict["Value"] = "null"
        self.data_dict["Initial_ESS_SoC"] = "null"
        self.data_dict["Initial_VAC_SoC"] = "null"
        self.data_dict["Behavior_Model"] = "null"

        self.remove_used_keys(ess_states_keys)
        self.remove_used_keys(vac_states_keys)

        self.validate_unit_consumption_assumption(vac_min, vac_steps)

    def generate_behaviour_model(self, plugged_time, unplugged_time, monte_carlo_repetition):
        plugged_time_mean = plugged_time.get("mean", None)
        plugged_time_std = plugged_time.get("std", None)

        assert plugged_time_mean, "mean value missing in Plugged_Time"
        assert plugged_time_std, "std value missing in Plugged_Time"

        unplugged_time_mean = unplugged_time.get("mean", None)
        unplugged_time_std = unplugged_time.get("std", None)

        assert unplugged_time_mean, "mean value missing in Unlugged_Time"
        assert unplugged_time_std, "std value missing in Unlugged_Time"

        self.simulator = partial(simulate,
                                 repetition=monte_carlo_repetition,
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

    def round_to_steps(self, value, min, step):
        self.logger.info("round values "+str(value)+" "+str(min)+" "+str(step))
        return round((value - min) / step) * step + min

