# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""
import json
import concurrent.futures
from pyomo.environ import *
from pyomo.opt import SolverStatus, TerminationCondition
import time, os



import pyutilib.subprocess.GlobalData

from optimization.controllerBaseThread import ControllerBaseThread
from optimization.idStatusManager import IDStatusManager
from pyutilib.services import TempfileManager

pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False


class OptControllerDiscrete(ControllerBaseThread):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds, optimization_type):
        self.number_of_workers = 1

        super().__init__(id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                         config, horizon_in_steps, dT_in_seconds, optimization_type)

    def optimize(self, count, solver_name, model_path):
        while not self.redisDB.get_bool(self.stop_signal_key):# and not self.stopRequest.isSet():
            action_handle_map = {}
            start_time_total = time.time()
            self.logger.info("waiting for data")
            data_dict = self.input.get_data(preprocess=False, redisDB=self.redisDB)  # blocking call
            self.logger.debug("Data is: " + json.dumps(data_dict, indent=4))
            if self.redisDB.get_bool(self.stop_signal_key):# or self.stopRequest.isSet():
                break

            start_time = time.time()
            # Creating an optimization instance with the referenced model
            try:
                futures = []
                with concurrent.futures.ProcessPoolExecutor(max_workers=self.number_of_workers) as executor:

                    futures.append(
                        executor.submit(OptControllerDiscrete.create_instance_and_solve, data_dict,
                                        solver_name, model_path))


                    for future in concurrent.futures.as_completed(futures):
                        try:
                            my_dict = future.result()
                            self.output.publish_data(self.id, my_dict, self.dT_in_seconds)
                            self.monitor.send_monitor_ping(self.control_frequency)
                        except Exception as exc:
                            self.logger.error("caused an exception: "+str(exc))


            except Exception as e:
                self.logger.error(e)


            start_time = time.time() - start_time
            self.logger.info("Time to run optimizer = " + str(start_time) + " sec.")

            self.erase_pyomo_files(self.pyomo_path)

            count += 1
            if self.repetition > 0 and count >= self.repetition:
                self.repetition_completed = True
                break

            self.logger.info("Optimization thread going to sleep for " + str(self.control_frequency) + " seconds")
            #time_spent = IDStatusManager.update_count(self.repetition, self.id, self.redisDB)
            final_time_total = time.time()
            sleep_time = self.control_frequency - int(final_time_total-start_time_total)
            if sleep_time > 0:
                self.logger.info("Optimization thread going to sleep for " + str(sleep_time) + " seconds")
                for i in range(sleep_time):
                    time.sleep(1)
                    if self.redisDB.get_bool(self.stop_signal_key):
                        break

    @staticmethod
    def create_instance_and_solve(data_dict, solver_name, absolute_path):
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
                        print("result is none")
                    elif (result.solver.status == SolverStatus.ok) and (
                            result.solver.termination_condition == TerminationCondition.optimal):
                        instance.solutions.load_from(result)

                        # * if solved get the values in dict
                        for v1 in instance.component_objects(Var, active=True):
                            varobject = getattr(instance, str(v1))
                            var_list = []
                            try:
                                # Try and add to the dictionary by key ref
                                for index in varobject:
                                    var_list.append(varobject[index].value)
                                my_dict[str(v1)] = var_list
                            except Exception as e:
                                print("error reading result " + str(e))
                    elif result.solver.termination_condition == TerminationCondition.infeasible:
                        # do something about it? or exit?
                        print("Termination condition is infeasible ")
                        continue
                    else:
                        print("Nothing fits ")
                        continue
            except Exception as e:
                print("Thread: " + str(e))


            return my_dict