# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""

import json
import os
import time
import uuid
import datetime
from itertools import product
import math

import numpy as np
from pyomo.environ import *
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition

import pyutilib.subprocess.GlobalData

from optimization.controllerBase import ControllerBase

pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False


class OptControllerStochastic(ControllerBase):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds, optimization_type):

        super().__init__(id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                         config, horizon_in_steps, dT_in_seconds, optimization_type)

    def optimize(self, action_handle_map, count, optsolver, solver_manager):
        while not self.stopRequest.isSet():
            self.logger.info("waiting for data")
            data_dict = self.input.get_data()  # blocking call

            if self.stopRequest.isSet():
                break

            ######################################
            # STOCHASTIC OPTIMIZATION

            start_time_offset = int(data_dict[None]["Start_Time"][None])

            forecast_pv = data_dict[None]["P_PV"]
            car_park = self.input_config_parser.car_park
            max_number_of_cars = car_park.number_of_cars

            behaviour_model = self.input_config_parser.simulator(time_resolution=self.dT_in_seconds,
                                                                 horizon=self.horizon_in_steps + start_time_offset,
                                                                 max_number_of_cars=max_number_of_cars)

            ess_soc_states = self.input_config_parser.ess_soc_states
            vac_soc_states = self.input_config_parser.vac_soc_states

            domain_range = (car_park.total_charging_stations_power * self.dT_in_seconds) / (
                car_park.vac_capacity) * 100

            ess_domain_range = 47  # ess max power / capacity

            ess_steps = self.input_config_parser.ess_steps
            ess_domain_min = - (math.floor(ess_domain_range / ess_steps) * ess_steps)
            ess_domain_max = (math.floor(ess_domain_range / ess_steps) * ess_steps) + ess_steps

            vac_steps = self.input_config_parser.vac_steps
            vac_domain_min = vac_soc_states[0]
            vac_domain_max = domain_range + vac_steps

            # ess_domain_min = ess_steps * round(ess_domain_min / ess_steps)
            # ess_domain_max = ess_steps * round(ess_domain_max / ess_steps)
            vac_domain_min = vac_steps * math.floor(vac_domain_min / vac_steps)
            vac_domain_max = vac_steps * math.floor(vac_domain_max / vac_steps)

            ess_decision_domain = np.arange(ess_domain_min, ess_domain_max, ess_steps).tolist()

            vac_decision_domain = np.arange(vac_domain_min, vac_domain_max, vac_steps).tolist()

            T = self.horizon_in_steps

            # Initialize empty lookup tables
            keylistforValue = [(t, s_ess, s_vac) for t, s_ess, s_vac in
                               product(list(range(0, T + 1)), ess_soc_states, vac_soc_states)]
            keylistforDecisions = [(t, s_ess, s_vac) for t, s_ess, s_vac in
                                   product(list(range(0, T)), ess_soc_states, vac_soc_states)]

            Value = dict.fromkeys(keylistforValue)
            Decision = dict.fromkeys(keylistforDecisions)

            for t, s_ess, s_vac in product(range(0, T), ess_soc_states, vac_soc_states):
                Decision[t, s_ess, s_vac] = {'PV': None, 'Grid': None, 'ESS': None, 'VAC': None}
                Value[t, s_ess, s_vac] = None

            for s_ess, s_vac in product(ess_soc_states, vac_soc_states):
                Value[T, s_ess, s_vac] = 1.0

            # self.logger.debug("Value "+str(Value))
            self.logger.debug("ess_decision_domain " + str(ess_decision_domain))
            self.logger.debug("vac_decision_domain " + str(vac_decision_domain))
            self.logger.debug("ess_soc_states " + str(ess_soc_states))
            self.logger.debug("vac_soc_states " + str(vac_soc_states))

            time_info = datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
            filename = f"log-{uuid.uuid1()}-{time_info}.json"

            input_log_filepath = os.path.join("/usr/src/app/logs", f"input-{filename}")
            output_log_filepath = os.path.join("/usr/src/app/logs", f"output-{filename}")
            decision_log_filepath = os.path.join("/usr/src/app/logs", f"decision-{filename}")

            with open(input_log_filepath, "w") as log_file:
                json.dump(data_dict, log_file, indent=4)

            stochastic_start_time = time.time()

            min_value = 100 * 0.2  # data_dict[None]["ESS_Min_SoC"]
            max_value = 100 * 1  # data_dict[None]["ESS_Max_SoC"]

            for timestep in reversed(range(start_time_offset, start_time_offset + self.horizon_in_steps)):
                self.logger.info(f"Timestep :#{timestep}")
                for ini_ess_soc, ini_vac_soc in product(ess_soc_states, vac_soc_states):

                    feasible_Pess = []  # Feasible charge powers to ESS under the given conditions
                    for p_ESS in ess_decision_domain:  # When decided charging with p_ESS
                        compare_value = ini_ess_soc - p_ESS
                        # self.logger.debug("min_value "+str(min_value))
                        # self.logger.debug("max_value " + str(max_value))
                        if min_value <= compare_value <= max_value:  # if the final ess_SoC is within the specified domain
                            feasible_Pess.append(p_ESS)
                    self.logger.debug("feasible p_ESS " + str(feasible_Pess))

                    feasible_Pvac = []  # Feasible charge powers to VAC under the given conditions
                    for p_VAC in vac_decision_domain:  # When decided charging with p_VAC
                        if p_VAC + ini_vac_soc <= max(
                                vac_soc_states):  # if the final vac_SoC is within the specified domain
                            feasible_Pvac.append(p_VAC)
                    self.logger.debug("feasible p_VAC " + str(feasible_Pvac))

                    data_dict[None]["Feasible_ESS_Decisions"] = {None: feasible_Pess}
                    data_dict[None]["Feasible_VAC_Decisions"] = {None: feasible_Pvac}

                    data_dict[None]["Initial_ESS_SoC"] = {None: ini_ess_soc}
                    # self.logger.debug("ini_ess_soc "+str(ini_ess_soc))

                    data_dict[None]["Initial_VAC_SoC"] = {None: ini_vac_soc}
                    # self.logger.debug("ini_vac_soc " + str(ini_vac_soc))

                    value_index = [(s_ess, s_vac) for t, s_ess, s_vac in Value.keys() if
                                   t == timestep + 1 - start_time_offset]
                    data_dict[None]["Value_Index"] = {None: value_index}

                    value = {v: Value[timestep + 1 - start_time_offset, v[0], v[1]] for v in value_index}
                    data_dict[None]["Value"] = value
                    # self.logger.debug("value "+str(value))

                    # * Updated
                    bm_idx = behaviour_model[timestep - start_time_offset].keys()
                    bm = behaviour_model[timestep - start_time_offset]

                    data_dict[None]["Behavior_Model_Index"] = {None: bm_idx}
                    data_dict[None]["Behavior_Model"] = bm

                    pv_forecast_for_current_timestep = forecast_pv[timestep]
                    data_dict[None]["P_PV"] = {None: pv_forecast_for_current_timestep}

                    # * Create Optimization instance

                    # Creating an optimization instance with the referenced model
                    try:
                        self.logger.debug("Creating an optimization instance")
                        instance = self.my_class.model.create_instance(data_dict)
                    except Exception as e:
                        self.logger.error("Error creating instance")
                        self.logger.error(e)
                    # instance = self.my_class.model.create_instance(self.data_path)
                    self.logger.info("Instance created with pyomo")

                    # * Queue the optimization instance

                    try:
                        # self.logger.info(instance.pprint())
                        action_handle = solver_manager.queue(instance, opt=optsolver)
                        self.logger.debug("Solver queue created " + str(action_handle))
                        self.logger.debug("solver queue actions = " + str(solver_manager.num_queued()))
                        action_handle_map[action_handle] = str(self.id)
                        self.logger.debug("Action handle map: " + str(action_handle_map))
                        # start_time = time.time()
                        # self.logger.debug("Optimization starting time: " + str(start_time))
                    except Exception as e:
                        self.logger.error("exception " + str(e))

                    # * Run the solver

                    # retrieve the solutions
                    for i in range(1):
                        this_action_handle = solver_manager.wait_any()
                        self.results = solver_manager.get_results(this_action_handle)
                        self.logger.debug("solver queue actions = " + str(solver_manager.num_queued()))
                        if this_action_handle in action_handle_map.keys():
                            self.solved_name = action_handle_map.pop(this_action_handle)
                        else:
                            self.solved_name = None

                    # * Check whether it is solved

                    # start_time = time.time() - start_time
                    # self.logger.info("Time to run optimizer = " + str(start_time) + " sec.")
                    if (self.results.solver.status == SolverStatus.ok) and (
                            self.results.solver.termination_condition == TerminationCondition.optimal):
                        # this is feasible and optimal
                        self.logger.info("Solver status and termination condition ok")
                        self.logger.debug("Results for " + self.solved_name + " with id: " + str(self.id))
                        self.logger.debug(self.results)
                        instance.solutions.load_from(self.results)

                        # * if solved get the values in dict

                        try:
                            my_dict = {}
                            for v in instance.component_objects(Var, active=True):
                                self.logger.debug("Variable in the optimization: " + str(v))
                                varobject = getattr(instance, str(v))
                                var_list = []
                                try:
                                    # Try and add to the dictionary by key ref
                                    for index in varobject:
                                        var_list.append(varobject[index].value)
                                    self.logger.debug("Identified variables " + str(var_list))
                                    my_dict[str(v)] = var_list
                                except Exception as e:
                                    self.logger.error(e)

                            Decision[timestep - start_time_offset, ini_ess_soc, ini_vac_soc]['Grid'] = \
                                my_dict["P_GRID_OUTPUT"][0]
                            Decision[timestep - start_time_offset, ini_ess_soc, ini_vac_soc]['PV'] = \
                                my_dict["P_PV_OUTPUT"][0]
                            Decision[timestep - start_time_offset, ini_ess_soc, ini_vac_soc]['ESS'] = \
                                my_dict["P_ESS_OUTPUT"][0]
                            Decision[timestep - start_time_offset, ini_ess_soc, ini_vac_soc]['VAC'] = \
                                my_dict["P_VAC_OUTPUT"][0]

                            Value[timestep - start_time_offset, ini_ess_soc, ini_vac_soc] = \
                                my_dict["P_PV_OUTPUT"][0]

                            self.logger.info("Done".center(80, "#"))
                            self.logger.info(f"Timestep :#{timestep} : {ini_ess_soc}, {ini_vac_soc} ")
                            self.logger.info("#" * 80)

                            # self.output.publish_data(self.id, my_dict)
                        except Exception as e:
                            self.logger.error(e)
                    elif self.results.solver.termination_condition == TerminationCondition.infeasible:
                        # do something about it? or exit?
                        self.logger.info("Termination condition is infeasible")
                    else:
                        self.logger.info("Nothing fits")

            initial_ess_soc_value = float(data_dict[None]["SoC_Value"][None])
            initial_vac_soc_value = float(data_dict[None]["VAC_SoC_Value"][None])

            p_pv = Decision[0, initial_ess_soc_value, initial_vac_soc_value]['PV']
            p_grid = Decision[0, initial_ess_soc_value, initial_vac_soc_value]['Grid']
            p_ess = Decision[0, initial_ess_soc_value, initial_vac_soc_value]['ESS']
            p_vac = Decision[0, initial_ess_soc_value, initial_vac_soc_value]['VAC']
            p_ev = {}

            print("Dynamic programming calculations")
            print("PV generation:", p_pv)
            print("Import:", p_grid)
            print("ESS discharge:", p_ess)
            print("VAC charging", p_vac)

            #############################################################################
            # This section distributes virtual capacity charging power into the cars plugged chargers in the station

            # detect which cars are connected to the chargers in the commercial charging station
            # calculate the maximum feasible charging power input under given SoC

            dT = data_dict[None]["dT"][None]
            ESS_Max_Charge = data_dict[None]["ESS_Max_Charge_Power"][None]
            ESS_Capacity = data_dict[None]["ESS_Capacity"][None]

            connections = self.input_config_parser.car_park.max_charge_power_calculator(dT)

            # Calculation of the feasible charging power at the commercial station
            max_power_for_cars = sum(connections.values())
            feasible_ev_charging_power = min(max_power_for_cars, p_vac)
            print("feasible_ev_charging_power" + str(feasible_ev_charging_power))
            print("max_power_for_cars " + str(max_power_for_cars))

            for charger, max_charge_power_of_car in connections.items():
                if feasible_ev_charging_power == 0:
                    p_ev[charger] = 0
                else:
                    power_output_of_charger = feasible_ev_charging_power * (
                            max_charge_power_of_car / max_power_for_cars)
                    p_ev[charger] = power_output_of_charger
                # print("power_output_of_charger "+str(power_output_of_charger)+"in charger "+str(charger) )
            #############################################################################

            #############################################################################
            # This section decides what to do with the non utilized virtual capacity charging power
            """
            # Power leftover: Non implemented part of virtual capacity charging power
            leftover_vac_charging_power = p_vac - feasible_ev_charging_power

            # Still leftover is attempted to be charged to the ESS
            ess_charger_limit = ESS_Max_Charge
            ess_capacity_limit = ((100 - initial_ess_soc_value) / 100) * (ESS_Capacity / dT)
            max_ess_charging_power = ess_capacity_limit - p_ess#min(ess_charger_limit, ess_capacity_limit, still_leftover)
            p_ess = p_ess + max_ess_charging_power

            # Leftover is attempted to be removed with less import
            less_import = min(p_grid, leftover_vac_charging_power)
            p_grid = p_grid - less_import

            # Some part could be still left
            still_leftover = leftover_vac_charging_power - less_import



            # Final leftover: if the ESS does not allow charging all leftover, final leftover will be compensated by PV curtailment
            final_leftover = still_leftover - max_ess_charging_power
            p_pv = p_pv - final_leftover
            """
            print("Implemented actions")
            print("PV generation:", p_pv)
            print("Import:", p_grid)
            print("ESS discharge:", p_ess)
            print("Real EV charging", feasible_ev_charging_power)

            stochastic_end_time = time.time()

            print("Time Information".center(80, "#"))
            print("")
            print(f"Start time: {stochastic_start_time}")
            print(f"End time: {stochastic_end_time}")
            execution_time = stochastic_end_time - stochastic_start_time
            print(f"Programming execution time: {execution_time}")
            print("")
            print("#" * 80)

            results = {
                "id": self.id,
                "p_pv": p_pv,
                "p_grid": p_grid,
                "p_ess": p_ess,
                "p_vac": p_vac,
                "feasible_ev_charging_power": feasible_ev_charging_power,
                "p_ev": p_ev,
                "execution_time": execution_time
            }

            with open(output_log_filepath, "w") as log_file:
                json.dump(results, log_file, indent=4)

            jsonDecision = {str(k): v for k, v in Decision.items()}

            with open(decision_log_filepath, "w") as log_file:
                json.dump(jsonDecision, log_file, indent=4)

            count += 1
            if self.repetition > 0 and count >= self.repetition:
                break

            self.logger.info("Optimization thread going to sleep for " + str(self.control_frequency) + " seconds")
            time_spent = self.update_count()
            for i in range(self.control_frequency - time_spent):
                time.sleep(1)
                if self.stopRequest.isSet():
                    break