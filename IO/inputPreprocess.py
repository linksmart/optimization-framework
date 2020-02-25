"""
Created on Mai 21 14:08 2019

@author: nishit
"""
import json
import os
from functools import partial

import numpy as np
import time

from profev.EV import EV
from profev.EVPark import EVPark
from profev.ChargingStation import ChargingStation
from profev.MonteCarloSimulator import simulate
from utils_intern.constants import Constants

from utils_intern.messageLogger import MessageLogger

class InputPreprocess:

    def __init__(self, id, mqtt_time_threshold, config):
        self.data_dict = {}
        self.logger = MessageLogger.get_logger(__name__, id)
        persist_real_data_path = "optimization/resources"
        persist_real_data_path = os.path.join("/usr/src/app", persist_real_data_path, id, "real")
        # persist_real_data_path = os.path.join(os.getcwd())
        self.persist_real_data_file = os.path.join(persist_real_data_path, "ev_info" + ".txt")
        self.ev_park = EVPark(id, self.persist_real_data_file)
        self.id = id
        self.mqtt_time_threshold = mqtt_time_threshold
        self.event_data = {}
        persist_base_file_path = config.get("IO", "persist.base.file.path")
        self.charger_base_path = os.path.join("/usr/src/app", persist_base_file_path, str(id), Constants.persisted_folder_name)
        self.charger_file_name = "chargers.json"

    def event_received(self, data):
        self.event_data.update(data)
        self.logger.info("events received = "+str(self.event_data))
        events_completed = []
        for key, value in data.items():
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, list):
                        timestamp = v[0]
                        event = v[1]
                        if isinstance(event, dict):
                            for charger_name, charger_value in event.items():
                                if "recharge" in key:
                                    if isinstance(charger_value, dict):
                                        if "recharge" in charger_value.keys():
                                            recharge_state = charger_value["recharge"]
                                            hosted_ev = None
                                            if "Hosted_EV" in charger_value.keys():
                                                hosted_ev = charger_value["Hosted_EV"]
                                            self.logger.debug("recharge_state " + str(recharge_state)+" for hosted ev "+str(hosted_ev) + " in charger "+str(charger_name))
                                            if charger_name in self.ev_park.chargers.keys():
                                                self.ev_park.chargers[charger_name].recharge_event(recharge_state,
                                                                                                   timestamp, hosted_ev)
                                                events_completed.append(key)
                                                self.logger.info("recharge event "+str(charger_value))
                                                self.logger.debug("ev_park.chargers "+str(self.ev_park.chargers[charger_name]))

        for event in events_completed:
            self.event_data.pop(event)
        self.logger.info("events to be considered later = "+str(self.event_data))

    def preprocess(self, data_dict, mqtt_timer):
        self.logger.info("data_dict = "+str(data_dict))
        self.data_dict = data_dict
        self.last_timesamps = mqtt_timer
        self.logger.info("mqtt timer = "+str(mqtt_timer))
        evs_list = self.generate_ev_classes()
        self.logger.debug("evs_list "+str(evs_list))
        self.ev_park.add_evs(evs_list)
        chargers_list = self.generate_charger_classes()
        self.ev_park.add_chargers(chargers_list)
        number_of_evs, vac_capacity = self.ev_park.get_num_of_cars(), self.ev_park.get_vac_capacity()
        self.data_dict["Number_of_Parked_Cars"] = {None: number_of_evs}
        self.data_dict["VAC_Capacity"] = {None: vac_capacity}

        self.event_received(self.event_data)

        self.process_uncertainty_data()
        #why is it different as for the other evs
        self.set_recharge_for_single_ev()


        for charger_id, charger in self.ev_park.chargers.items():
            self.logger.info(charger.__str__())

        self.persist_charger_data()

        #time.sleep(60)
        self.logger.info("data_dict = " + str(self.data_dict))
        return self.data_dict

    def get_last_timestamp(self, partial_key):
        timestamp = -1
        for k, v in self.last_timesamps.items():
            if partial_key in k:
                timestamp = v
                break
        return timestamp

    def validate_unit_consumption_assumption(self, vac_min, vac_step):
        self.logger.info("data_dict : "+str(self.data_dict))
        if "Unit_Consumption_Assumption" in self.data_dict.keys():
            uac = float(self.data_dict["Unit_Consumption_Assumption"][None])
            self.logger.debug("Unit consumption assumption "+str(uac)+ " vac_min "+str(vac_min)+" vac_step "+str(vac_step))
            if not (((uac - vac_min) / vac_step).is_integer()):
                raise Exception("Unit_Consumption_Assumption should be a valid step of VAC_steps")
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

    def generate_charger_classes(self):
        chargers_list = []
        update = {}
        for k, v in self.data_dict.items():
            if self.is_charger(v):
                charger = k
                charger_dict = v
                last_timestamp = self.get_last_timestamp(charger)
                self.logger.info("charger "+ str(charger)+" last timestamp: "+str(last_timestamp))
                self.logger.info("charger dict "+str(charger_dict))
                max_charging_power_kw = charger_dict.get("Max_Charging_Power_kW", None)
                hosted_ev = charger_dict.get("Hosted_EV", None)
                soc = charger_dict.get("SoC", None)
                ev_unplugged = False
                """if isinstance(soc, dict):
                    # did not receive soc value from mqtt
                    # check time threshold for EV unplugged
                    if self.exceeded_time_threshold(last_timestamp):
                        # EV unplugged
                        ev_unplugged = True"""
                if not (isinstance(soc, float) or isinstance(soc, int)):
                    soc = None
                    ev_unplugged = True
                assert max_charging_power_kw, "Incorrect input: Max_Charging_Power_kW missing for charger: " + str(charger)
                self.logger.debug("hosted_ev "+str(hosted_ev)+ " with soc "+str(soc) + " ev_unplugged "+str(ev_unplugged))
                chargers_list.append(ChargingStation(charger, max_charging_power_kw, hosted_ev, soc))
                v["SoC"] = soc
                update[k] = v
        self.data_dict.update(update)
        for c in chargers_list:
            self.logger.debug(c)
        self.check_evs_in_charging_stations(chargers_list)
        for c in chargers_list:
            self.logger.debug(c)
        return chargers_list

    def check_evs_in_charging_stations(self, cs_list):
        for cs in cs_list:
            for new_cs in cs_list:
                if not cs == new_cs:
                    if cs.hosted_ev == new_cs.hosted_ev:
                        if cs.soc == None:
                            cs.unplug()
                        if new_cs.soc == None:
                            new_cs.unplug()



    def exceeded_time_threshold(self, last_time):
        if last_time - time.time() > self.mqtt_time_threshold:
            return True
        else:
            return False

    """def generate_ev_classes(self):
        evs_list = []
        ev_keys = []
        for k, v in self.data_dict.items():
            if self.is_ev(v):
                ev = k
                ev_dict = v
                ev_keys.append(k)
                battery_capacity = ev_dict.get("Battery_Capacity_kWh", None)
                assert battery_capacity, "Incorrect input: Battery_Capacity_kWh missing for EV: " + str(ev)
                ev_no_base = self.remove_key_base(ev)
                self.logger.debug("ev_no_base "+str(ev_no_base))
                if not ev_no_base == None:
                    evs_list.append(EV(self.id, ev_no_base, battery_capacity))
        self.remove_used_keys(ev_keys)
        return evs_list"""

    def generate_ev_classes(self):
        ev_data_from_file = None
        if os.path.exists(self.persist_real_data_file):
            ev_data_from_file = self.read_data(self.persist_real_data_file)
            self.logger.debug("Data from file read: "+str(self.persist_real_data_file))

        evs_list = []
        ev_keys = []
        for k, v in self.data_dict.items():
            # print("k "+str(k) + " v " + str(v))
            if self.is_ev(v):
                ev = k
                ev_dict = v
                ev_keys.append(k)
                battery_capacity = ev_dict.get("Battery_Capacity_kWh", None)
                assert battery_capacity, "Incorrect input: Battery_Capacity_kWh missing for EV: " + str(ev)
                self.logger.debug("ev "+str(ev))
                ev_no_base = self.remove_key_base(ev)
                soc = None
                if not ev_data_from_file == None:
                    if ev in ev_data_from_file.keys():
                        soc = ev_data_from_file[ev]
                if not soc == None and not ev_no_base == None:
                    self.logger.debug("soc "+str(soc)+" ev_no_base "+str(ev_no_base))
                    evs_list.append(EV(self.id, ev_no_base, battery_capacity, soc))
                else:
                    if not ev_no_base == None:
                        evs_list.append(EV(self.id, ev_no_base, battery_capacity))

        return evs_list

    def read_data(self, filepath):
        try:
            with open(filepath, "r") as file:
                data = file.read()
            return json.loads(data)
        except Exception as e:
            self.logger.error("Read input file exception: " + str(e))

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

        ess_min, ess_max, ess_steps, ess_soc_states = self.generate_states(ess_states, "ESS_States")
        vac_min, vac_max, vac_steps, vac_soc_states = self.generate_states(vac_states, "VAC_States")

        self.ess_steps = ess_steps
        self.vac_steps = vac_steps
        self.ess_soc_states = ess_soc_states
        self.vac_soc_states = vac_soc_states

        VAC_SoC_Value_override = None
        if "VAC_SoC_Value_override" in self.data_dict.keys():
            VAC_SoC_Value_override = self.data_dict["VAC_SoC_Value_override"][None]
        vac_soc_value = self.ev_park.calculate_vac_soc_value(vac_soc_value_override=VAC_SoC_Value_override)
        vac_soc_value = self.round_to_steps(vac_soc_value, vac_min, vac_steps)

        soc_value_key = None
        for key, value in self.data_dict["SoC_Value"].items():
            soc_value_key = key
            break

        soc_value = self.data_dict["SoC_Value"][soc_value_key]
        soc_value = self.round_to_steps(soc_value, ess_min, ess_steps)

        if vac_soc_value < vac_min:
            vac_soc_value = vac_min

        if soc_value < ess_min:
            soc_value = ess_min

        self.logger.info("vac_soc_value = " + str(vac_soc_value))
        self.logger.info("soc_value = " + str(soc_value))

        self.data_dict["SoC_Value"] = {None: soc_value}
        self.data_dict["VAC_SoC_Value"] = {None: vac_soc_value}

        self.data_dict["VAC_States_Min"] = {None: vac_min}
        self.data_dict["Value"] = "null"
        self.data_dict["Initial_ESS_SoC"] = "null"
        self.data_dict["Initial_VAC_SoC"] = "null"
        self.data_dict["Behavior_Model"] = "null"


        self.remove_used_keys(ess_states_keys)
        self.remove_used_keys(vac_states_keys)

        self.validate_unit_consumption_assumption(vac_min, vac_steps)

    def set_recharge_for_single_ev(self):
        recharge = self.ev_park.single_ev_recharge()
        self.data_dict["Recharge"] = {None: recharge}
        self.logger.info("Recharge value: "+str(recharge))

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

        assert min_value != None, "Min value missing in " + str(state_name)
        assert max_value, "Max value missing in " + str(state_name)
        assert steps, "Steps value missing in " + str(state_name)

        #min_value = int(min_value)
        #max_value = int(max_value)

        return (min_value, max_value, steps, np.arange(min_value, max_value + steps, steps).tolist())

    def round_to_steps(self, value, min, step):
        self.logger.info("round values "+str(value)+" "+str(min)+" "+str(step))
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
                    self.logger.debug("charger data persisted "+file_path)
                    #print("charger data persisted "+file_path)
        except Exception as e:
            self.logger.error("error persisting charger data "+str(e))