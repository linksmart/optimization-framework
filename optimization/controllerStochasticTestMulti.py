# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""

import time
import concurrent.futures
from itertools import product
import math
import gc

import numpy as np
from pyomo.environ import *
from pyomo.opt import SolverStatus, TerminationCondition


import pyutilib.subprocess.GlobalData

from optimization.controllerBase import ControllerBase
from optimization.idStatusManager import IDStatusManager

from pyutilib.services import TempfileManager

pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False

ins_dict  = {}

class OptControllerStochastic(ControllerBase):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds, optimization_type, single_ev):
        self.single_ev = single_ev
        self.number_of_workers = int(config.get("SolverSection", "stochastic.multi.workers", fallback=6))
        super().__init__(id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                         config, horizon_in_steps, dT_in_seconds, optimization_type)



    def get_values(self, T, ess_soc_states, vac_soc_states, position_states, max_number_of_cars):
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

        return (behaviour_model, Value, Decision)

    def calculate_internal_values(self, timestep, Value, behaviour_model, ess_soc_states, vac_soc_states,position_states):
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

            bm_idx = list(behaviour_model[timestep].keys())

            bm = behaviour_model[timestep]

            ess_vac_product = product(ess_soc_states, vac_soc_states)

        return (value_index, value,bm_idx, bm, ess_vac_product)

    def find_decision_domain_ess(self, ess_vac_product, ess_decision_domain, min_value, max_value ):
        for combination in ess_vac_product:
            feasible_Pess = []  # Feasible charge powers to ESS under the given conditions

            if self.single_ev:
                #recharge_value = int(data_dict[None]["Recharge"][None])
                ini_ess_soc, ini_vac_soc, position = combination

                for p_ESS in ess_decision_domain:  # When decided charging with p_ESS
                    compare_value = ini_ess_soc - p_ESS
                    # self.logger.debug("min_value "+str(min_value))
                    # self.logger.debug("max_value " + str(max_value))
                    if min_value <= compare_value <= max_value:  # if the final ess_SoC is within the specified domain
                        feasible_Pess.append(p_ESS)
                # self.logger.debug("feasible p_ESS " + str(feasible_Pess))
            else:
                ini_ess_soc, ini_vac_soc = combination

                for p_ESS in ess_decision_domain:  # When decided charging with p_ESS
                    compare_value = ini_ess_soc - p_ESS
                    # self.logger.debug("min_value "+str(min_value))
                    # self.logger.debug("max_value " + str(max_value))
                    if min_value <= compare_value <= max_value:  # if the final ess_SoC is within the specified domain
                        feasible_Pess.append(p_ESS)
                # self.logger.debug("feasible p_ESS " + str(feasible_Pess))
        return feasible_Pess

    def start_optimizer(self, optsolver, solver_manager, instance_list):
        action_handles = []
        action_handle_map = {}
        for instance in instance_list:
            action_handle = solver_manager.queue(instance["instance"], opt=optsolver, keepfiles=False, tee=False,
                                                 load_solutions=False)
            action_handle_map[action_handle] = instance
            action_handles.append(action_handle)

        solver_manager.wait_all(action_handles)
        return (action_handles, action_handle_map)


    def calculate_vac_domain(self, domain_range):
        vac_soc_states = self.input.inputPreprocess.vac_soc_states
        vac_steps = self.input.inputPreprocess.vac_steps
        vac_domain_min = vac_soc_states[0]
        vac_domain_max = domain_range + vac_steps

        # ess_domain_min = ess_steps * round(ess_domain_min / ess_steps)
        # ess_domain_max = ess_steps * round(ess_domain_max / ess_steps)
        vac_domain_min = vac_steps * math.floor(vac_domain_min / vac_steps)
        vac_domain_max = vac_steps * math.floor(vac_domain_max / vac_steps)

        vac_decision_domain = np.arange(vac_domain_min, vac_domain_max, vac_steps).tolist()
        vac_decision_domain_n = np.arange(vac_domain_min, vac_domain_max, vac_steps)

        return (vac_soc_states, vac_decision_domain, vac_decision_domain_n)

    def calculate_ess_domain(self, data_dict, domain_range):
        ess_soc_states = self.input.inputPreprocess.ess_soc_states
        ess_max_power = data_dict[None]["ESS_Max_Charge_Power"][None]
        ess_min_power = data_dict[None]["ESS_Max_Discharge_Power"][None]
        ess_capacity = data_dict[None]["ESS_Capacity"][None]
        # self.logger.debug("ess_capacity: "+str(ess_capacity)+" ess_min_power: "+str(ess_min_power)+ " ess_max_power: "+str(ess_max_power))
        ess_domain_range_max = math.floor((ess_max_power / ess_capacity) * 100)
        ess_domain_range_min = math.floor((ess_min_power / ess_capacity) * 100)

        ess_steps = self.input.inputPreprocess.ess_steps
        ess_domain_min = - (math.floor(ess_domain_range_min / ess_steps) * ess_steps)
        ess_domain_max = (math.floor(ess_domain_range_max / ess_steps) * ess_steps) + ess_steps

        ess_decision_domain = np.arange(ess_domain_min, ess_domain_max, ess_steps).tolist()

        return (ess_soc_states, ess_decision_domain)

    def optimize(self, count, solver_name, model_path):
        self.logger.debug("##############  testsf")
        while not self.redisDB.get_bool(self.stop_signal_key):# and not self.stopRequest.isSet():
            start_time_total = time.time()
            self.logger.debug("number of workers = " + str(self.number_of_workers))
            self.logger.info("waiting for data")
            data_dict = self.input.get_data(preprocess=True)  # blocking call

            if self.redisDB.get_bool(self.stop_signal_key):# or self.stopRequest.isSet():
                break

            ######################################
            # STOCHASTIC OPTIMIZATION

            ev_park = self.input.inputPreprocess.ev_park
            max_number_of_cars = ev_park.get_num_of_cars()

            position_states = [0, 1]

            domain_range = (ev_park.total_charging_stations_power * self.dT_in_seconds) / (
                ev_park.get_vac_capacity() * 3600) * 100

            vac_soc_states, vac_decision_domain, vac_decision_domain_n = self.calculate_vac_domain(domain_range)

            ess_soc_states, ess_decision_domain = self.calculate_ess_domain(data_dict, domain_range)

            T = self.horizon_in_steps

            behaviour_model, Value, Decision = self.get_values(T, ess_soc_states, vac_soc_states,  position_states, max_number_of_cars)



            stochastic_start_time = time.time()

            min_value = 100 * float(data_dict[None]["ESS_Min_SoC"][None])
            max_value = 100 * float(data_dict[None]["ESS_Max_SoC"][None])

            max_vac_soc_states = max(vac_soc_states)

            reverse_steps = reversed(range(0, self.horizon_in_steps))
            for timestep in reverse_steps:

                if self.redisDB.get_bool(self.stop_signal_key):
                    break
                else:
                    self.logger.info("Timestep :#"+str(timestep))

                    value_index, value,bm_idx, bm, ess_vac_product = self.calculate_internal_values(timestep, Value, behaviour_model, ess_soc_states, vac_soc_states,
                                              position_states)
                    data_dict[None]["Value_Index"] = {None: value_index}
                    data_dict[None]["Value"] = value
                    data_dict[None]["Behavior_Model_Index"] = {None: bm_idx}
                    data_dict[None]["Behavior_Model"] = bm

                    data_dict[None]["Timestep"] = {None: timestep}

                    # retrieve the solutions
                    try:
                        futures = []
                        with concurrent.futures.ProcessPoolExecutor(max_workers=self.number_of_workers) as executor:
                            if self.single_ev:
                                for combination in ess_vac_product:
                                    ini_ess_soc, ini_vac_soc, position = combination
                                    futures.append(
                                        executor.submit(OptControllerStochastic.create_instance_and_solve, data_dict,
                                                        ess_decision_domain, min_value, max_value, vac_decision_domain,
                                                        vac_decision_domain_n, max_vac_soc_states, timestep, True,
                                                        solver_name, model_path, ini_ess_soc, ini_vac_soc, position))
                            else:
                                for combination in ess_vac_product:
                                    ini_ess_soc, ini_vac_soc = combination
                                    futures.append(
                                        executor.submit(OptControllerStochastic.create_instance_and_solve, data_dict,
                                                        ess_decision_domain, min_value, max_value, vac_decision_domain,
                                                        vac_decision_domain_n, max_vac_soc_states, timestep, False,
                                                        solver_name, model_path, ini_ess_soc, ini_vac_soc))

                            for future in concurrent.futures.as_completed(futures):
                                try:
                                    d, v = future.result()
                                    Value.update(v)
                                    Decision.update(d)
                                except Exception as exc:
                                    self.logger.error("caused an exception: "+str(exc))


                    except Exception as e:
                        self.logger.error(e)

                    value_index.clear()
                    value.clear()
                    bm.clear()

                    # erasing files from pyomo
                    folder = "/usr/src/app/logs/pyomo_"+str(self.id)
                    self.erase_pyomo_files(folder)

            """
            with open("/usr/src/app/optimization/resources/Value_p.txt", "w") as f:
                f.write(str(Value))
            self.logger.info("written to file")
            """

            if self.redisDB.get_bool(self.stop_signal_key):
                break
            else:
                initial_ess_soc_value = float(data_dict[None]["SoC_Value"][None])
                self.logger.debug("initial_ess_soc_value " + str(initial_ess_soc_value))
                initial_vac_soc_value = float(data_dict[None]["VAC_SoC_Value"][None])
                self.logger.debug("initial_vac_soc_value " + str(initial_vac_soc_value))

                if self.single_ev:
                    recharge_value = int(data_dict[None]["Recharge"][None])
                    result_key = (0, initial_ess_soc_value, initial_vac_soc_value, recharge_value)
                else:
                    result_key = (0, initial_ess_soc_value, initial_vac_soc_value)

                p_pv = Decision[result_key]['PV']
                p_grid = Decision[result_key]['Grid']
                p_ess = Decision[result_key]['ESS']
                p_vac = Decision[result_key]['VAC']

                Decision.clear()
                Value.clear()

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
                data_dict.clear()
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

                self.logger.debug("Implemented actions")
                self.logger.debug("PV generation:" + str(p_pv))
                self.logger.debug("Grid before:" + str(p_grid))
                p_grid = feasible_ev_charging_power - p_pv - p_ess
                self.logger.debug("Grid after:" + str(p_grid))
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
                socs = ev_park.charge_ev(p_ev, self.dT_in_seconds)
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

                for key, value in socs.items():
                    ev_id = ev_park.get_hosted_ev(key)
                    if ev_id:
                        results_publish[key + "/SoC"] = {"bn": "chargers/" + key, "n": ev_id + "/SoC", "v": [value]}

                self.output.publish_data(self.id, results_publish, self.dT_in_seconds)

                results.clear()
                ev_park = None
                results_publish.clear()

                #with open(output_log_filepath, "w") as log_file:
                    #json.dump(results, log_file, indent=4)

                #jsonDecision = {str(k): v for k, v in Decision.items()}

                #with open(decision_log_filepath, "w") as log_file:
                    #json.dump(jsonDecision, log_file, indent=4)

                count += 1
                if self.repetition > 0 and count >= self.repetition:
                    self.repetition_completed = True
                    break

                time_spent = IDStatusManager.update_count(self.repetition, self.id, self.redisDB)
                final_time_total = time.time()
                sleep_time = self.control_frequency - int(final_time_total - start_time_total)
                if sleep_time > 0:
                    self.logger.info("Optimization thread going to sleep for " + str(sleep_time) + " seconds")
                    for i in range(sleep_time):
                        time.sleep(1)
                        if self.redisDB.get_bool(self.stop_signal_key): #or self.stopRequest.isSet():
                            break

    @staticmethod
    def create_instance_and_solve(data_dict, ess_decision_domain, min_value, max_value, vac_decision_domain,
                                  vac_decision_domain_n, max_vac_soc_states, timestep, single_ev, solver_name,
                                  absolute_path, ini_ess_soc, ini_vac_soc, position=None):
        feasible_Pess = []  # Feasible charge powers to ESS under the given conditions

        if single_ev:
            recharge_value = int(data_dict[None]["Recharge"][None])

            for p_ESS in ess_decision_domain:  # When decided charging with p_ESS
                compare_value = ini_ess_soc - p_ESS
                # self.logger.debug("min_value "+str(min_value))
                # self.logger.debug("max_value " + str(max_value))
                if min_value <= compare_value <= max_value:  # if the final ess_SoC is within the specified domain
                    feasible_Pess.append(p_ESS)
            # self.logger.debug("feasible p_ESS " + str(feasible_Pess))

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

            for p_ESS in ess_decision_domain:  # When decided charging with p_ESS
                compare_value = ini_ess_soc - p_ESS
                # self.logger.debug("min_value "+str(min_value))
                # self.logger.debug("max_value " + str(max_value))
                if min_value <= compare_value <= max_value:  # if the final ess_SoC is within the specified domain
                    feasible_Pess.append(p_ESS)
            # self.logger.debug("feasible p_ESS " + str(feasible_Pess))

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

        data_dict[None]["Initial_VAC_SoC"] = {None: ini_vac_soc}
        # self.logger.debug("ini_vac_soc " + str(ini_vac_soc))

        final_ev_soc = ini_vac_soc - data_dict[None]["Unit_Consumption_Assumption"][None]
        if final_ev_soc < data_dict[None]["VAC_States_Min"][None]:
            final_ev_soc = data_dict[None]["VAC_States_Min"][None]

        data_dict[None]["final_ev_soc"] = {None: final_ev_soc}


        v = str(timestep) + "_" + str(ini_ess_soc) + "_" + str(ini_vac_soc)
        result = None
        instance = None
        my_dict = {}
        while True:
            try:
                if True:
                    optsolver = SolverFactory(solver_name)
                    spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
                    module = spec.loader.load_module(spec.name)
                    my_class = getattr(module, 'Model')
                    instance = my_class.model.create_instance(data_dict)
                    result = optsolver.solve(instance)
                    if result is None:
                        print("result is none for " + str(v) + " repeat")
                    elif (result.solver.status == SolverStatus.ok) and (
                            result.solver.termination_condition == TerminationCondition.optimal):
                        instance.solutions.load_from(result)

                        # * if solved get the values in dict
                        for v1 in instance.component_objects(Var, active=True):
                            # self.logger.debug("Variable in the optimization: " + str(v))
                            varobject = getattr(instance, str(v1))
                            var_list = []
                            try:
                                # Try and add to the dictionary by key ref
                                for index in varobject:
                                    var_list.append(varobject[index].value)
                                # self.logger.debug("Identified variables " + str(var_list))
                                my_dict[str(v1)] = var_list
                            except Exception as e:
                                print("error reading result " + str(e))
                    elif result.solver.termination_condition == TerminationCondition.infeasible:
                        # do something about it? or exit?
                        print("Termination condition is infeasible " + v + " repeat")
                        continue
                    else:
                        print("Nothing fits " + v + " repeat")
                        continue
            except Exception as e:
                print("Thread: " + v + " " + str(e))


            if single_ev:
                combined_key = (timestep, ini_ess_soc, ini_vac_soc, position)
            else:
                combined_key = (timestep, ini_ess_soc, ini_vac_soc)

            Decision = {combined_key: {}}
            Decision[combined_key]['Grid'] = my_dict["P_GRID_OUTPUT"][0]
            Decision[combined_key]['PV'] = my_dict["P_PV_OUTPUT"][0]
            Decision[combined_key]['ESS'] = my_dict["P_ESS_OUTPUT"][0]
            Decision[combined_key]['VAC'] = my_dict["P_VAC_OUTPUT"][0]

            Value = {combined_key: {}}
            Value[combined_key] = my_dict["P_PV_OUTPUT"][0]
            return (Decision, Value)
