# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""

import json
from pyomo.environ import *
from pyomo.opt import SolverStatus, TerminationCondition
import time

import pyutilib.subprocess.GlobalData

from optimization.controllerBase import ControllerBase
from optimization.idStatusManager import IDStatusManager

pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False


class OptControllerMPC(ControllerBase):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds, optimization_type):

        super().__init__(id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                         config, horizon_in_steps, dT_in_seconds, optimization_type)

    def optimize(self, count, solver_name, model_path):
        optsolver = None
        solver_manager = None
        while not self.redisDB.get_bool(self.stop_signal_key) and not self.stopRequest.isSet():
            action_handle_map = {}
            self.logger.info("waiting for data")
            data_dict = self.input.get_data(preprocess=False)  # blocking call
            self.logger.debug("Data is: " + json.dumps(data_dict, indent=4))
            if self.redisDB.get_bool(self.stop_signal_key) or self.stopRequest.isSet():
                break

            # Creating an optimization instance with the referenced model
            try:
                self.logger.debug("Creating an optimization instance")
                instance = self.my_class.model.create_instance(data_dict)
            except Exception as e:
                self.logger.error(e)
            # instance = self.my_class.model.create_instance(self.data_path)
            self.logger.info("Instance created with pyomo")

            run_count = 0
            while True:
                try:
                    # self.logger.info(instance.pprint())
                    action_handle = solver_manager.queue(instance, opt=optsolver)
                    self.logger.debug("Solver queue created " + str(action_handle))
                    self.logger.debug("solver queue actions = " + str(solver_manager.num_queued()))
                    action_handle_map[action_handle] = str(self.id)
                    self.logger.debug("Action handle map: " + str(action_handle_map))
                    start_time = time.time()
                    self.logger.debug("Optimization starting time: " + str(start_time))
                    break
                except Exception as e:
                    self.logger.error("exception " + str(e))
                    if run_count == 5:
                        raise e
                    time.sleep(5)
                run_count += 1

            ###retrieve the solutions
            for i in range(1):
                this_action_handle = solver_manager.wait_any()
                self.results = solver_manager.get_results(this_action_handle)
                self.logger.debug("solver queue actions = " + str(solver_manager.num_queued()))
                if this_action_handle in action_handle_map.keys():
                    self.solved_name = action_handle_map.pop(this_action_handle)
                else:
                    self.solved_name = None

            start_time = time.time() - start_time
            self.logger.info("Time to run optimizer = " + str(start_time) + " sec.")
            if (self.results.solver.status == SolverStatus.ok) and (
                    self.results.solver.termination_condition == TerminationCondition.optimal):
                # this is feasible and optimal
                self.logger.info("Solver status and termination condition ok")
                self.logger.debug("Results for " + self.solved_name + " with id: " + str(self.id))
                self.logger.debug(self.results)
                instance.solutions.load_from(self.results)
                try:
                    my_dict = {}
                    for v in instance.component_objects(Var, active=True):
                        # self.logger.debug("Variable in the optimization: "+ str(v))
                        varobject = getattr(instance, str(v))
                        var_list = []
                        try:
                            # Try and add to the dictionary by key ref
                            for index in varobject:
                                var_list.append(varobject[index].value)
                            my_dict[str(v)] = var_list
                        except Exception as e:
                            self.logger.error(e)
                            # Append new index to currently existing items
                            # my_dict = {**my_dict, **{v: list}}

                    if "stop_system" not in my_dict.keys() or (
                            "stop_system" in my_dict.keys() and my_dict["stop_system"][0] == 0.0):
                        self.logger.debug("model.stop_system false")
                        self.output.publish_data(self.id, my_dict, self.dT_in_seconds)
                    else:
                        self.logger.debug("model.stop_system true")
                except Exception as e:
                    self.logger.error(e)
            elif self.results.solver.termination_condition == TerminationCondition.infeasible:
                # do something about it? or exit?
                self.logger.info("Termination condition is infeasible")
            else:
                self.logger.info("Nothing fits")

            count += 1
            if self.repetition > 0 and count >= self.repetition:
                self.repetition_completed = True
                break

            self.logger.info("Optimization thread going to sleep for " + str(self.control_frequency) + " seconds")
            time_spent = IDStatusManager.update_count(self.repetition, self.id, self.redisDB)
            for i in range(self.control_frequency - time_spent):
                time.sleep(1)
                if self.redisDB.get_bool(self.stop_signal_key) or self.stopRequest.isSet():
                    break