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
import gc

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

            bm_idx = behaviour_model[timestep].keys()

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

    def create_instance(self, data_dict, ess_vac_product, ess_decision_domain, min_value, max_value, vac_decision_domain, vac_decision_domain_n, max_vac_soc_states):
        instance_list = []
        for combination in ess_vac_product:


            if self.single_ev:
                recharge_value = int(data_dict[None]["Recharge"][None])
                ini_ess_soc, ini_vac_soc, position = combination

                feasible_Pess = []  # Feasible charge powers to ESS under the given conditions
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
                ini_ess_soc, ini_vac_soc = combination

                feasible_Pess = []  # Feasible charge powers to ESS under the given conditions
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
            # self.logger.debug("ini_ess_soc "+str(ini_ess_soc))

            data_dict[None]["Initial_VAC_SoC"] = {None: ini_vac_soc}
            # self.logger.debug("ini_vac_soc " + str(ini_vac_soc))

            final_ev_soc = ini_vac_soc - data_dict[None]["Unit_Consumption_Assumption"][None]
            if final_ev_soc < data_dict[None]["VAC_States_Min"][None]:
                final_ev_soc = data_dict[None]["VAC_States_Min"][None]

            data_dict[None]["final_ev_soc"] = {None: final_ev_soc}

            # Creating an optimization instance with the referenced model
            try:
                # self.logger.debug("Creating an optimization instance")
                # self.logger.debug("input data: " + str(data_dict))
                instance = self.my_class.model.create_instance(data_dict)
                if self.single_ev:
                    instance_dict = {"instance": instance, "ess_soc": ini_ess_soc, "vac_soc": ini_vac_soc, "position": position}
                else:
                    instance_dict = {"instance": instance, "ess_soc": ini_ess_soc, "vac_soc": ini_vac_soc}
                instance_list.append(instance_dict)
                """if self.single_ev:
                    inst = Instance(str(instance_id), ini_ess_soc, ini_vac_soc, position=position,
                                    instance=instance)
                else:
                    inst = Instance(str(instance_id), ini_ess_soc, ini_vac_soc, instance=instance)

                # instance_info.append(inst)
                instance_info[instance] = inst

                instance_id += 1"""
            except Exception as e:
                self.logger.error(e)



        return instance_list

    def start_optimizer(self, optsolver, solver_manager, instance_list):
        action_handles = []
        action_handle_info = {}
        action_handle_info_list = []
        instance_map = {}
        action_handle_map = {}
        for instance in instance_list:
            action_handle = solver_manager.queue(instance["instance"], opt=optsolver, keepfiles=False, tee=False,
                                                 load_solutions=False)
            action_handle_map[action_handle] = instance
            action_handles.append(action_handle)

        solver_manager.wait_all(action_handles)
        return (action_handles, action_handle_map)


    def get_result_from_optimization(self, instance, result):
        instance.solutions.load_from(result)

        # * if solved get the values in dict

        my_dict = {}
        for v in instance.component_objects(Var, active=True):
            # self.logger.debug("Variable in the optimization: " + str(v))
            varobject = getattr(instance, str(v))
            var_list = []
            try:
                # Try and add to the dictionary by key ref
                for index in varobject:
                    var_list.append(varobject[index].value)
                # self.logger.debug("Identified variables " + str(var_list))
                my_dict[str(v)] = var_list

            except Exception as e:
                self.logger.error("error reading result " + str(e))
        return my_dict

    def get_results(self, timestep, solver_manager, action_handles, action_handle_map, Decision, Value):
        for action_handle in action_handles:
            # for inst in instance_info:
            # self.logger.debug("num queued " + str(solver_manager.num_queued()))
            result = solver_manager.get_results(action_handle)

            instance_object = action_handle_map[action_handle]
            # self.logger.debug("instance object "+str(instance_object))
            instance = instance_object["instance"]
            ini_ess_soc = instance_object["ess_soc"]  # instance_info[instance].ini_ess_soc
            ini_vac_soc = instance_object["vac_soc"]  # instance_info[instance].ini_vac_soc
            if self.single_ev:
                position = instance_object["position"]  # instance_info[instance].position

            # self.logger.debug("solver status "+str(result.solver.status))
            # self.logger.debug("termination condition " + str(result.solver.termination_condition))

            if (result.solver.status == SolverStatus.ok) and (
                    result.solver.termination_condition == TerminationCondition.optimal):
                # this is feasible and optimal
                # self.logger.info("Solver status and termination condition ok")
                # self.logger.debug("Results for " + inst.instance_id + " with id: " + str(self.id))
                # self.logger.debug(result)
                # instance.solutions.load_from(result)
                my_dict = self.get_result_from_optimization(instance, result)

                if self.single_ev:
                    combined_key = (timestep, ini_ess_soc, ini_vac_soc, position)
                else:
                    combined_key = (timestep, ini_ess_soc, ini_vac_soc)

                Decision[combined_key]['Grid'] = my_dict["P_GRID_OUTPUT"][0]
                Decision[combined_key]['PV'] = my_dict["P_PV_OUTPUT"][0]
                Decision[combined_key]['ESS'] = my_dict["P_ESS_OUTPUT"][0]
                Decision[combined_key]['VAC'] = my_dict["P_VAC_OUTPUT"][0]

                Value[combined_key] = my_dict["P_PV_OUTPUT"][0]
                # self.logger.debug("Value "+str(Value))
                return (Decision, Value)

            elif result.solver.termination_condition == TerminationCondition.infeasible:
                # do something about it? or exit?
                self.logger.info("Termination condition is infeasible")
                return 1
            else:
                self.logger.info("Nothing fits")
                return 1

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

    #def optimize(self, action_handle_map, count, optsolver, solver_manager):
    def optimize(self, count, optsolver, solver_manager, solver_name, model_path):

        while not self.redisDB.get_bool(self.stop_signal_key) and not self.stopRequest.isSet():
            start_time_total = time.time()

            self.logger.info("waiting for data")
            data_dict = self.input.get_data(preprocess=True)  # blocking call

            if self.redisDB.get_bool(self.stop_signal_key) or self.stopRequest.isSet():
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


            #del keylistforValue
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
                start_time_timestep = time.time()
                self.logger.info("Timestep :#"+str(timestep))

                value_index, value,bm_idx, bm, ess_vac_product = self.calculate_internal_values(timestep, Value, behaviour_model, ess_soc_states, vac_soc_states,
                                          position_states)

                data_dict[None]["Value_Index"] = {None: value_index}
                data_dict[None]["Value"] = value
                data_dict[None]["Behavior_Model_Index"] = {None: bm_idx}
                bm_idx=None
                data_dict[None]["Behavior_Model"] = bm
                data_dict[None]["Timestep"] = {None: timestep}

                medium_time_timestep = time.time()
                instance_list = self.create_instance(data_dict, ess_vac_product, ess_decision_domain, min_value, max_value, vac_decision_domain, vac_decision_domain_n, max_vac_soc_states)
                final_time_timestep = time.time()
                medium = medium_time_timestep - start_time_timestep
                final= final_time_timestep -start_time_timestep

                # retrieve the solutions
                try:
                    #action_handles, action_handle_map = self.start_optimizer(optsolver,solver_manager, instance_list)
                    #for action_handle in action_handles:
                    for instance_object in instance_list:
                        #for inst in instance_info:
                        # self.logger.debug("num queued " + str(solver_manager.num_queued()))
                        #result = solver_manager.get_results(action_handle)

                        #instance_object = action_handle_map[action_handle]
                        # self.logger.debug("instance object "+str(instance_object))
                        instance = instance_object["instance"]
                        result=optsolver.solve(instance, tee=False, keepfiles=False, load_solutions=False)
                        ini_ess_soc = instance_object["ess_soc"]  # instance_info[instance].ini_ess_soc
                        ini_vac_soc = instance_object["vac_soc"]  # instance_info[instance].ini_vac_soc
                        if self.single_ev:
                            position = instance_object["position"]  # instance_info[instance].position

                        if (result.solver.status == SolverStatus.ok) and (
                                result.solver.termination_condition == TerminationCondition.optimal):
                            # this is feasible and optimal
                            my_dict = self.get_result_from_optimization(instance, result)

                            if self.single_ev:
                                combined_key = (timestep, ini_ess_soc, ini_vac_soc, position)
                            else:
                                combined_key = (timestep, ini_ess_soc, ini_vac_soc)

                            Decision[combined_key]['Grid'] = my_dict["P_GRID_OUTPUT"][0]
                            Decision[combined_key]['PV'] = my_dict["P_PV_OUTPUT"][0]
                            Decision[combined_key]['ESS'] = my_dict["P_ESS_OUTPUT"][0]
                            Decision[combined_key]['VAC'] = my_dict["P_VAC_OUTPUT"][0]

                            Value[combined_key] = my_dict["P_PV_OUTPUT"][0]

                        elif result.solver.termination_condition == TerminationCondition.infeasible:
                            # do something about it? or exit?
                            self.logger.info("Termination condition is infeasible")
                        else:
                            self.logger.info("Nothing fits")

                    value_index.clear()
                    value.clear()
                    bm.clear()
                    #action_handle_map.clear()
                    #action_handles.clear()
                    instance_list.clear()
                    my_dict.clear()
                    ess_vac_product = None



                except Exception as e:
                    self.logger.error(e)


                #self.logger.debug("status "+str(solver_manager.get_status(this_action_handle)))
                #self.logger.debug("num queued " + str(solver_manager.num_queued()))

                gc.collect()

                # erasing files from pyomo
                self.erase_pyomo_files()

                final_time_timestep_after_result = time.time()
                final_after_result = final_time_timestep_after_result - final_time_timestep
                self.logger.debug("medium time " + str(medium) + " with instances " + str(final)+ " after result "+str(final_after_result))

                #with open("/usr/src/app/optimization/resources/Decision_p.txt", "w") as f:
                    #f.write(str(Decision))
                #with open("/usr/src/app/optimization/resources/Value_p.txt", "w") as f:
                    #f.write(str(Value))
                #self.logger.info("written to file")
                #break


            #del action_handle_map
            #del action_handles
            #del instance_list
            #del my_dict
            behaviour_model.clear()
            ess_decision_domain = None
            vac_decision_domain = None
            vac_decision_domain_n = None
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

            """Decision = None
            Value = None
            ess_vac_product = None
            ess_decision_domain = None
            vac_decision_domain = None
            vac_decision_domain_n = None
            behaviour_model = None"""

            reverse_steps=None
            Decision.clear()
            Value.clear()




            """del reverse_steps
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
            #del keylistforDecisions"""

            gc.collect()

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
            #del data_dict
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

            results.clear()
            ev_park = None
            results_publish.clear()
            #del ev_park
            #del results_publish

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