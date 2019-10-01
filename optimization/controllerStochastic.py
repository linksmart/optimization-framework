# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""

import json
import os
import sys
import time
import uuid
import datetime
from itertools import product
import math

import numpy as np
from pyomo.environ import *
from pyomo.opt import SolverStatus, TerminationCondition


import pyutilib.subprocess.GlobalData

from optimization.controllerBase import ControllerBase
from optimization.idStatusManager import IDStatusManager
from optimization.instance import Instance

pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False


class OptControllerStochastic(ControllerBase):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds, optimization_type, single_ev):
        self.single_ev = single_ev

        super().__init__(id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                         config, horizon_in_steps, dT_in_seconds, optimization_type)

    def optimize(self, count, optsolver, solver_manager, solver_name, model_path):
        while not self.redisDB.get_bool(self.stop_signal_key) and not self.stopRequest.isSet():
            action_handle_map = {}
            start_time_total = time.time()
            self.logger.info("waiting for data")
            data_dict = self.input.get_data(preprocess=True)  # blocking call

            if self.redisDB.get_bool(self.stop_signal_key) or self.stopRequest.isSet():
                break

            ######################################
            # STOCHASTIC OPTIMIZATION

            ev_park = self.input.inputPreprocess.ev_park
            max_number_of_cars = ev_park.get_num_of_cars()

            ess_soc_states = self.input.inputPreprocess.ess_soc_states
            vac_soc_states = self.input.inputPreprocess.vac_soc_states
            position_states = [0, 1]

            domain_range = (ev_park.total_charging_stations_power * self.dT_in_seconds) / (
                ev_park.get_vac_capacity() * 3600) * 100

            ess_max_power = data_dict[None]["ESS_Max_Charge_Power"][None]
            ess_min_power = data_dict[None]["ESS_Max_Discharge_Power"][None]
            ess_capacity = data_dict[None]["ESS_Capacity"][None]
            #self.logger.debug("ess_capacity: "+str(ess_capacity)+" ess_min_power: "+str(ess_min_power)+ " ess_max_power: "+str(ess_max_power))
            ess_domain_range_max = math.floor((ess_max_power / ess_capacity) * 100)
            ess_domain_range_min = math.floor((ess_min_power / ess_capacity) * 100)

            ess_steps = self.input.inputPreprocess.ess_steps
            ess_domain_min = - (math.floor(ess_domain_range_min / ess_steps) * ess_steps)
            ess_domain_max = (math.floor(ess_domain_range_max / ess_steps) * ess_steps) + ess_steps

            vac_steps = self.input.inputPreprocess.vac_steps
            vac_domain_min = vac_soc_states[0]
            vac_domain_max = domain_range + vac_steps

            # ess_domain_min = ess_steps * round(ess_domain_min / ess_steps)
            # ess_domain_max = ess_steps * round(ess_domain_max / ess_steps)
            vac_domain_min = vac_steps * math.floor(vac_domain_min / vac_steps)
            vac_domain_max = vac_steps * math.floor(vac_domain_max / vac_steps)

            #self.logger.debug("vac domain : "+str(vac_domain_min)+ " "+ str(vac_domain_max)+ " " + str(vac_steps))

            ess_decision_domain = np.arange(ess_domain_min, ess_domain_max, ess_steps).tolist()
            vac_decision_domain = np.arange(vac_domain_min, vac_domain_max, vac_steps).tolist()
            vac_decision_domain_n = np.arange(vac_domain_min, vac_domain_max, vac_steps)

            T = self.horizon_in_steps

            if self.single_ev:
                behaviour_model = self.input.inputPreprocess.simulator(time_resolution=self.dT_in_seconds,
                                                                       horizon=self.horizon_in_steps,
                                                                       single_ev=True)
                # Initialize empty lookup tables
                keylistforValue = [(t, s_ess, s_vac, s_pos) for t, s_ess, s_vac, s_pos in
                                   product(list(range(0, T + 1)), ess_soc_states, vac_soc_states, position_states)]
                keylistforDecisions = [(t, s_ess, s_vac, s_pos) for t, s_ess, s_vac, s_pos in
                                       product(list(range(0, T)), ess_soc_states, vac_soc_states, position_states)]

                Value = dict.fromkeys(keylistforValue)
                Decision = dict.fromkeys(keylistforDecisions)

                for t, s_ess, s_vac, s_pos in product(range(0, T), ess_soc_states, vac_soc_states, position_states):
                    Decision[t, s_ess, s_vac, s_pos] = {'PV': None, 'Grid': None, 'ESS': None, 'VAC': None}
                    Value[t, s_ess, s_vac, s_pos] = None

                for s_ess, s_vac, s_pos in product(ess_soc_states, vac_soc_states, position_states):
                    Value[T, s_ess, s_vac, s_pos] = 5.0
            else:
                behaviour_model = self.input.inputPreprocess.simulator(time_resolution=self.dT_in_seconds,
                                                                       horizon=self.horizon_in_steps,
                                                                       max_number_of_cars=max_number_of_cars)
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
            #self.logger.debug("ess_decision_domain " + str(ess_decision_domain))
            #self.logger.debug("vac_decision_domain " + str(vac_decision_domain))
            #self.logger.debug("ess_soc_states " + str(ess_soc_states))
            #self.logger.debug("vac_soc_states " + str(vac_soc_states))

            #time_info = datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
            #filename = "log-"+str(uuid.uuid1())+"-"+str(time_info)+".json"

            #input_log_filepath = os.path.join("/usr/src/app/logs", "input-"+str(filename))
            #output_log_filepath = os.path.join("/usr/src/app/logs", "output-"+str(filename))
            #decision_log_filepath = os.path.join("/usr/src/app/logs", "decision-"+str(filename))

            #with open(input_log_filepath, "w") as log_file:
                #json.dump(data_dict, log_file, indent=4)

            stochastic_start_time = time.time()

            min_value = 100 * float(data_dict[None]["ESS_Min_SoC"][None])
            max_value = 100 * float(data_dict[None]["ESS_Max_SoC"][None])

            max_vac_soc_states = max(vac_soc_states)
            reverse_steps = reversed(range(0, self.horizon_in_steps))
            for timestep in reverse_steps:
                self.logger.info("Timestep :#"+str(timestep))

                instance_id = 0
                instance_info = {}

                if self.single_ev:
                    value_index = [(s_ess, s_vac, s_pos) for t, s_ess, s_vac, s_pos in Value.keys() if
                                   t == timestep + 1]

                    value = {v: Value[timestep + 1, v[0], v[1], v[2]] for v in value_index}

                    bm_idx = [(pos, next_pos) for t, pos, next_pos in behaviour_model.keys() if
                              t == timestep]

                    bm = {v: behaviour_model[timestep, v[0], v[1]] for v in bm_idx}

                    ess_vac_product = product(ess_soc_states, vac_soc_states, position_states)
                else:
                    value_index = [(s_ess, s_vac) for t, s_ess, s_vac in Value.keys() if
                                   t == timestep + 1]

                    value = {v: Value[timestep + 1, v[0], v[1]] for v in value_index}

                    bm_idx = behaviour_model[timestep].keys()

                    bm = behaviour_model[timestep]

                    ess_vac_product = product(ess_soc_states, vac_soc_states)

                data_dict[None]["Value_Index"] = {None: value_index}
                data_dict[None]["Value"] = value
                data_dict[None]["Behavior_Model_Index"] = {None: bm_idx}
                data_dict[None]["Behavior_Model"] = bm

                data_dict[None]["Timestep"] = {None: timestep}

                for combination in ess_vac_product:
                    feasible_Pess = []  # Feasible charge powers to ESS under the given conditions

                    if self.single_ev:
                        recharge_value = int(data_dict[None]["Recharge"][None])
                        ini_ess_soc, ini_vac_soc, position = combination

                        for p_ESS in ess_decision_domain:  # When decided charging with p_ESS
                            compare_value = ini_ess_soc - p_ESS
                            # self.logger.debug("min_value "+str(min_value))
                            # self.logger.debug("max_value " + str(max_value))
                            if min_value <= compare_value <= max_value:  # if the final ess_SoC is within the specified domain
                                feasible_Pess.append(p_ESS)
                        #self.logger.debug("feasible p_ESS " + str(feasible_Pess))

                        feasible_Pvac = []  # Feasible charge powers to VAC under the given conditions
                        if recharge_value == 1:
                            # When decided charging with p_VAC
                            if vac_decision_domain[0] <= max_vac_soc_states - ini_vac_soc:
                                # if the final vac_SoC is within the specified domain
                                index = np.searchsorted(vac_decision_domain_n, max_vac_soc_states - ini_vac_soc)
                                feasible_Pvac = vac_decision_domain[0:index + 1]
                        else:
                            feasible_Pvac.append(0)
                        # self.logger.debug("feasible p_VAC " + str(feasible_Pvac))

                    else:
                        ini_ess_soc, ini_vac_soc = combination

                        for p_ESS in ess_decision_domain:  # When decided charging with p_ESS
                            compare_value = ini_ess_soc - p_ESS
                            # self.logger.debug("min_value "+str(min_value))
                            # self.logger.debug("max_value " + str(max_value))
                            if min_value <= compare_value <= max_value:  # if the final ess_SoC is within the specified domain
                                feasible_Pess.append(p_ESS)
                        #self.logger.debug("feasible p_ESS " + str(feasible_Pess))

                        feasible_Pvac = []  # Feasible charge powers to VAC under the given conditions
                        # When decided charging with p_VAC
                        if vac_decision_domain[0] <= max_vac_soc_states - ini_vac_soc:
                            # if the final vac_SoC is within the specified domain
                            index = np.searchsorted(vac_decision_domain_n, max_vac_soc_states - ini_vac_soc)
                            feasible_Pvac = vac_decision_domain[0:index + 1]

                        # self.logger.debug("feasible p_VAC " + str(feasible_Pvac))

                    data_dict[None]["Feasible_ESS_Decisions"] = {None: feasible_Pess}
                    data_dict[None]["Feasible_VAC_Decisions"] = {None: feasible_Pvac}

                    data_dict[None]["Initial_ESS_SoC"] = {None: ini_ess_soc}
                    #self.logger.debug("ini_ess_soc "+str(ini_ess_soc))

                    data_dict[None]["Initial_VAC_SoC"] = {None: ini_vac_soc}
                    #self.logger.debug("ini_vac_soc " + str(ini_vac_soc))

                    final_ev_soc = ini_vac_soc - data_dict[None]["Unit_Consumption_Assumption"][None]
                    if final_ev_soc < data_dict[None]["VAC_States_Min"][None]:
                        final_ev_soc = data_dict[None]["VAC_States_Min"][None]

                    data_dict[None]["final_ev_soc"] = {None: final_ev_soc}

                    # Creating an optimization instance with the referenced model
                    try:
                        #self.logger.debug("Creating an optimization instance")
                        #self.logger.debug("input data: " + str(data_dict))
                        instance = self.my_class.model.create_instance(data_dict)

                    except pyutilib.common.ApplicationError:  # pragma:nocover
                        self.logger.error("Error creating instance")
                        self.logger.error("Pyutilib error")
                        err = sys.exc_info()[1]
                        self.logger.error(err)
                    #except Exception as e:
                        #self.logger.error("Error creating instance")
                        #self.logger.error(e)
                    # instance = self.my_class.model.create_instance(self.data_path)
                    #self.logger.info("Instance created with pyomo")

                    # * Queue the optimization instance

                    try:
                        #self.logger.info(instance.pprint())
                        action_handle = solver_manager.queue(instance, opt=optsolver, warmstart=False)#, tee=False, logfile="/usr/src/app/logs/pyomo.log")
                        #self.logger.debug("Solver queue created " + str(action_handle))
                        #self.logger.debug("solver queue actions = " + str(solver_manager.num_queued()))
                        #action_handle_map[action_handle] = str(self.id)
                        action_handle_map[action_handle] = str(instance_id)
                        #self.logger.debug("Action handle map: " + str(action_handle_map))
                        # start_time = time.time()
                        # self.logger.debug("Optimization starting time: " + str(start_time))
                        if self.single_ev:
                            inst = Instance(str(instance_id), ini_ess_soc, ini_vac_soc, position=position, instance=instance)
                        else:
                            inst = Instance(str(instance_id), ini_ess_soc, ini_vac_soc, instance=instance)

                        #instance_info.append(inst)
                        instance_info[instance_id] = inst

                        instance_id += 1

                    except pyutilib.common.ApplicationError:  # pragma:nocover
                        self.logger.error("Error creating queue")
                        self.logger.error("Pyutilib error")
                        err = sys.exc_info()[1]
                        self.logger.error(err)
                    #except Exception as e:
                        #self.logger.error("exception " + str(e))

                    # * Run the solver

                # retrieve the solutions
                for i in range(instance_id):
                    try:


                        this_action_handle = solver_manager.wait_any()
                        result = solver_manager.get_results(this_action_handle)
                        #self.logger.debug("solver queue actions = " + str(solver_manager.num_queued()))
                        solved_name = None
                        if this_action_handle in action_handle_map.keys():
                            solved_name = action_handle_map.pop(this_action_handle)
                        if solved_name:
                            inst = instance_info[int(solved_name)]
                            #instance_info[int(solved_name)].addResult(result)

                            #result = inst.result
                            ini_ess_soc = inst.ini_ess_soc
                            ini_vac_soc = inst.ini_vac_soc
                            position = inst.position
                            instance = inst.instance

                            if (result.solver.status == SolverStatus.ok) and (
                                    result.solver.termination_condition == TerminationCondition.optimal):
                                # this is feasible and optimal
                                #self.logger.info("Solver status and termination condition ok")
                                #self.logger.debug("Results for " + inst.instance_id + " with id: " + str(self.id))
                                #self.logger.debug(result)
                                instance.solutions.load_from(result)

                                # * if solved get the values in dict

                                try:
                                    my_dict = {}
                                    for v in instance.component_objects(Var, active=True):
                                        #self.logger.debug("Variable in the optimization: " + str(v))
                                        varobject = getattr(instance, str(v))
                                        var_list = []
                                        try:
                                            # Try and add to the dictionary by key ref
                                            for index in varobject:
                                                var_list.append(varobject[index].value)
                                            #self.logger.debug("Identified variables " + str(var_list))
                                            my_dict[str(v)] = var_list
                                        except Exception as e:
                                            self.logger.error("error reading result "+str(e))

                                    if self.single_ev:
                                        combined_key = (timestep, ini_ess_soc, ini_vac_soc, position)
                                    else:
                                        combined_key = (timestep, ini_ess_soc, ini_vac_soc)

                                    Decision[combined_key]['Grid'] = my_dict["P_GRID_OUTPUT"][0]
                                    Decision[combined_key]['PV'] = my_dict["P_PV_OUTPUT"][0]
                                    Decision[combined_key]['ESS'] = my_dict["P_ESS_OUTPUT"][0]
                                    Decision[combined_key]['VAC'] = my_dict["P_VAC_OUTPUT"][0]

                                    Value[combined_key] = my_dict["P_PV_OUTPUT"][0]

                                    #self.logger.info("Done".center(80, "#"))
                                    #self.logger.info("Timestep :#"+str(timestep)+" : "+str(ini_ess_soc)+", "+str(ini_vac_soc))
                                    #self.logger.info("#" * 80)

                                    # self.output.publish_data(self.id, my_dict)
                                except Exception as e:
                                    self.logger.error("error setting decision or value "+str(e))
                            elif result.solver.termination_condition == TerminationCondition.infeasible:
                                # do something about it? or exit?
                                self.logger.info("Termination condition is infeasible")
                            else:
                                self.logger.info("Nothing fits")
                    except pyutilib.common.ApplicationError:  # pragma:nocover
                        self.logger.error("Pyutilib error")
                        err = sys.exc_info()[1]
                        self.logger.error(err)

                #solver_manager.queue.clear()
                del instance_info




                # erasing files from pyomo
                folder = "/usr/src/app/logs/pyomo"
                for the_file in os.listdir(folder):
                    file_path = os.path.join(folder, the_file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        # elif os.path.isdir(file_path): shutil.rmtree(file_path)
                    except Exception as e:
                        self.logger.error(e)
                #with open("/usr/src/app/optimization/resources/Decision_p.txt", "w") as f:
                    #f.write(str(Decision))
                #with open("/usr/src/app/optimization/resources/Value_p.txt", "w") as f:
                    #f.write(str(Value))
                #self.logger.info("written to file")
                #break

            initial_ess_soc_value = float(data_dict[None]["SoC_Value"][None])
            initial_vac_soc_value = float(data_dict[None]["VAC_SoC_Value"][None])

            if self.single_ev:
                recharge_value = int(data_dict[None]["Recharge"][None])
                result_key = (0, initial_ess_soc_value, initial_vac_soc_value, recharge_value)
            else:
                result_key = (0, initial_ess_soc_value, initial_vac_soc_value)

            p_pv = Decision[result_key]['PV']
            p_grid = Decision[result_key]['Grid']
            p_ess = Decision[result_key]['ESS']
            p_vac = Decision[result_key]['VAC']

            del reverse_steps
            del Decision
            del Value
            del value
            del value_index
            del bm_idx
            del bm
            del ess_vac_product
            del ess_decision_domain
            del vac_decision_domain
            del vac_decision_domain_n
            del behaviour_model
            del keylistforDecisions
            del keylistforValue

            p_ev = {}

            self.logger.debug("Dynamic programming calculations")
            self.logger.debug("PV generation:" + str(p_pv))
            self.logger.debug("Import:" + str(p_grid))
            self.logger.debug("ESS discharge:" + str(p_ess))
            self.logger.debug("VAC charging" + str(p_vac))

            #############################################################################
            # This section distributes virtual capacity charging power into the cars plugged chargers in the station

            # detect which cars are connected to the chargers in the commercial charging station
            # calculate the maximum feasible charging power input under given SoC

            dT = data_dict[None]["dT"][None]
            ESS_Max_Charge = data_dict[None]["ESS_Max_Charge_Power"][None]
            ESS_Capacity = data_dict[None]["ESS_Capacity"][None]
            del data_dict
            connections = ev_park.max_charge_power_calculator(dT)

            # Calculation of the feasible charging power at the commercial station
            max_power_for_cars = sum(connections.values())
            feasible_ev_charging_power = min(max_power_for_cars, p_vac)
            self.logger.debug("feasible_ev_charging_power" + str(feasible_ev_charging_power))
            self.logger.debug("max_power_for_cars " + str(max_power_for_cars))

            for charger, max_charge_power_of_car in connections.items():
                if feasible_ev_charging_power == 0:
                    p_ev[charger] = 0
                else:
                    power_output_of_charger = feasible_ev_charging_power * (
                            max_charge_power_of_car / max_power_for_cars)
                    p_ev[charger] = power_output_of_charger
                # self.logger.debug("power_output_of_charger "+str(power_output_of_charger)+"in charger "+str(charger) )
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
            self.logger.debug("Implemented actions")
            self.logger.debug("PV generation:" + str(p_pv))
            self.logger.debug("Import:" + str(p_grid))
            self.logger.debug("ESS discharge:" + str(p_ess))
            self.logger.debug("Real EV charging" + str(feasible_ev_charging_power))

            stochastic_end_time = time.time()

            self.logger.debug("Time Information".center(80, "#"))
            self.logger.debug("")
            self.logger.debug("Start time: "+str(stochastic_start_time))
            self.logger.debug("End time: "+str(stochastic_end_time))
            execution_time = stochastic_end_time - stochastic_start_time
            self.logger.debug("Programming execution time: "+str(execution_time))
            self.logger.debug("")
            self.logger.debug("#" * 80)

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

            # update soc
            ev_park.charge_ev(p_ev, self.dT_in_seconds)
            #time.sleep(60)

            results_publish = {
                "p_pv": [p_pv],
                "p_grid": [p_grid],
                "p_ess": [p_ess],
                "p_vac": [p_vac],
                "feasible_ev_charging_power": [feasible_ev_charging_power],
                "execution_time": [execution_time]
            }

            for key, value in p_ev.items():
                ev_id = ev_park.get_hosted_ev(key)
                if ev_id:
                    results_publish[key+"/p_ev"] = {"bn":"chargers/"+key, "n":ev_id+"/p_ev", "v":[value]}

            self.output.publish_data(self.id, results_publish, self.dT_in_seconds)

            del results
            del ev_park
            del results_publish

            #with open(output_log_filepath, "w") as log_file:
                #json.dump(results, log_file, indent=4)

            #jsonDecision = {str(k): v for k, v in Decision.items()}

            #with open(decision_log_filepath, "w") as log_file:
                #json.dump(jsonDecision, log_file, indent=4)

            count += 1
            if self.repetition > 0 and count >= self.repetition:
                self.repetition_completed = True
                break

            self.logger.info("Optimization thread going to sleep for " + str(self.control_frequency) + " seconds")
            time_spent = IDStatusManager.update_count(self.repetition, self.id, self.redisDB)
            final_time_total = time.time()
            sleep_time = self.control_frequency - int(final_time_total - start_time_total)
            if sleep_time > 0:
                for i in range(sleep_time):
                    time.sleep(1)
                    if self.redisDB.get_bool(self.stop_signal_key) or self.stopRequest.isSet():
                        break