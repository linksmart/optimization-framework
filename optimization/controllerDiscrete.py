# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""
import json

from pyomo.environ import *
from pyomo.opt import SolverStatus, TerminationCondition
import time, os


import pyutilib.subprocess.GlobalData

from optimization.controllerBaseThread import ControllerBaseThread
from optimization.idStatusManager import IDStatusManager

pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False


class OptControllerDiscrete(ControllerBaseThread):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds, optimization_type):
        self.infeasibility_repetition_count = config.getint("SolverSection", "discrete.infeasibility.repeat.count", fallback=2)
        super().__init__(id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                         config, horizon_in_steps, dT_in_seconds, optimization_type)

    def optimize(self, count, solver_name, model_path):
        infeasibility_repeated = 0
        while not self.redisDB.get_bool(self.stop_signal_key):# and not self.stopRequest.isSet():
            repeat_flag = False
            action_handle_map = {}
            start_time_total = time.time()
            self.logger.info("waiting for data")
            data_dict = self.input.get_data(preprocess=False, redisDB=self.redisDB)  # blocking call
            self.logger.debug("Data is: " + json.dumps(data_dict, indent=4))
            if self.redisDB.get_bool(self.stop_signal_key) or self.redisDB.get("End ofw") == "True":
                break

            start_time = time.time()
            # Creating an optimization instance with the referenced model
            try:
                optsolver = SolverFactory(solver_name)
                if solver_name == "ipopt":
                    optsolver.options['max_iter'] = 1000
                    optsolver.options['max_cpu_time'] = 120
                    
                #spec = importlib.util.spec_from_file_location(model_path, model_path)
                #module = spec.loader.load_module(spec.name)
                mod = __import__(model_path, fromlist=['Model'])
                my_class = getattr(mod, 'Model')
                self.logger.debug("Creating an optimization instance")

                cnt = 0
                instance = my_class.model.create_instance(data_dict)
                self.logger.debug("instance constructed: " + str(instance.is_constructed())+" in count "+str(cnt))
                result = optsolver.solve(instance, keepfiles=True)

            except Exception as e:
                self.logger.error(e)


            start_time = time.time() - start_time
            self.logger.info("Time to run optimizer = " + str(start_time) + " sec.")
            if result and (result.solver.status == SolverStatus.ok) and (
                    result.solver.termination_condition == TerminationCondition.optimal):
                # this is feasible and optimal
                self.logger.info("Solver status and termination condition ok")

                instance.solutions.load_from(result)
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

                    self.output.publish_data(self.id, my_dict, self.dT_in_seconds)
                    self.monitor.send_monitor_ping(self.control_frequency)
                except Exception as e:
                    self.logger.error(e)
            elif result.solver.termination_condition == TerminationCondition.infeasible:
                # do something about it? or exit?
                self.logger.info("Termination condition is infeasible")
                repeat_flag = True
            elif result.solver.termination_condition == TerminationCondition.maxIterations:
                # do something about it? or exit?
                self.logger.info("Termination condition is maxIteration limit")
                repeat_flag = True
            elif result.solver.termination_condition == TerminationCondition.maxTimeLimit:
                # do something about it? or exit?
                self.logger.info("Termination condition is maxTimeLimit")
                repeat_flag = True
            else:
                self.logger.info("Nothing fits")

            self.erase_pyomo_files(self.pyomo_path)

            if repeat_flag:
                infeasibility_repeated += 1
                if infeasibility_repeated <= self.infeasibility_repetition_count:
                    continue

            infeasibility_repeated = 0

            count += 1
            if self.repetition > 0 and count >= self.repetition:
                self.repetition_completed = True
                break

            self.logger.info("Optimization thread going to sleep for " + str(self.control_frequency) + " seconds")
            time_spent = IDStatusManager.update_count(self.repetition, self.id, self.redisDB)
            final_time_total = time.time()
            sleep_time = self.control_frequency - int(final_time_total-start_time_total)
            self.logger.info("Final time " + str(final_time_total) + " start time "+str(start_time_total)+
                             " run time "+str(int(final_time_total-start_time_total)))
            self.logger.info("Actual sleep time " + str(sleep_time) + " seconds")
            if sleep_time > 0:
                for i in range(sleep_time):
                    time.sleep(1)
                    if self.redisDB.get_bool(self.stop_signal_key):
                        break
                    if self.redisDB.get("End ofw") == "True":
                        break
