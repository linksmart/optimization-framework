# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 15:05:36 2018

@author: garagon
"""

import importlib.util
import json
import threading

import os
from pyomo.environ import *
from pyomo.opt import SolverFactory
from pyomo.opt.parallel import SolverManagerFactory
from pyomo.opt import SolverStatus, TerminationCondition
import subprocess
import time

from IO.inputController import InputController
from IO.outputController import OutputController
from IO.redisDB import RedisDB
from optimization.InvalidModelException import InvalidModelException
import logging
from threading import Event

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class OptController(threading.Thread):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds):
        # threading.Thread.__init__(self)
        super(OptController, self).__init__()
        logger.info("Initializing optimization controller")
        # Loading variables
        self.id = id
        self.results = ""
        self.model_path = model_path
        self.solver_name = solver_name
        self.control_frequency = control_frequency
        self.repetition = repetition
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.output_config = output_config
        self.input_config_parser = input_config_parser
        self.stopRequest = threading.Event()
        self.finish_status = False
        self.redisDB = RedisDB()
        self.lock_key = "id_lock"

        try:
            # dynamic load of a class
            logger.info("This is the model path: " + self.model_path)
            module = self.path_import2(self.model_path)
            logger.info(getattr(module, 'Model'))
            self.my_class = getattr(module, 'Model')

        except Exception as e:
            logger.error(e)
            raise InvalidModelException("model is invalid/contains python syntax errors")

        self.output = OutputController(self.output_config)
        self.input = InputController(self.id, self.input_config_parser, config, self.control_frequency,
                                     self.horizon_in_steps, self.dT_in_seconds)

    # Importint a class dynamically
    def path_import2(self, absolute_path):
        spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
        module = spec.loader.load_module(spec.name)
        return module

    def join(self, timeout=None):
        self.stopRequest.set()
        super(OptController, self).join(timeout)

    def Stop(self, id):
        self.input.Stop(id)
        if self.isAlive():
            self.join(1)

    def update_count(self):
        st = time.time()
        if self.repetition > 0:
            path = "/usr/src/app/utils/ids_status.txt"
            if os.path.exists(path):
                try:
                    if self.redisDB.get_lock(self.lock_key, self.id):
                        data = []
                        with open(path, "r") as f:
                            data = f.readlines()
                        if len(data) > 0:
                            line = None
                            for s in data:
                                if self.id in s and "repetition\": -1" not in s:
                                    line = s
                                    break
                            if line is not None:
                                i = data.index(line)
                                line = json.loads(line.replace("\n", ""))
                                line["repetition"] -= 1
                                data[i] = json.dumps(line, sort_keys=True, separators=(', ', ': ')) + "\n"
                                with open(path, "w") as f:
                                    f.writelines(data)
                except Exception as e:
                    logging.error("error updating count in file " + str(e))
                finally:
                    self.redisDB.release_lock(self.lock_key, self.id)
        st = int(time.time() - st)
        return st

    # Start the optimization process and gives back a result
    def run(self):
        logger.info("Starting optimization controller")
        pyro_mip_server = None
        solver_manager = None
        return_msg = "success"
        try:
            ###pyro_mip_server
            pyro_mip_server = subprocess.Popen(["/usr/local/bin/pyro_mip_server"])
            logger.debug("Pyro mip server started: " + str(pyro_mip_server))

            ###maps action handles to instances
            action_handle_map = {}

            #####create a solver
            optsolver = SolverFactory(self.solver_name)
            logger.debug("Solver factory: " + str(optsolver))
            # optsolver.options["max_iter"]=5000
            logger.info("solver instantiated with " + self.solver_name)

            ###create a solver manager
            solver_manager = SolverManagerFactory('pyro')

            if solver_manager is None:
                logger.error("Failed to create a solver manager")
            else:
                logger.debug("Solver manager created: " + str(solver_manager))

            count = 0
            logger.info("This is the id: " + self.id)
            while not self.stopRequest.isSet():
                logger.info("waiting for data")
                data_dict = self.input.get_data(self.id)  # blocking call
                #logger.debug("Data is: " + json.dumps(data_dict, indent=4))
                if self.stopRequest.isSet():
                    break

                # Creating an optimization instance with the referenced model
                try:
                    logger.debug("Creating an optimization instance")
                    instance = self.my_class.model.create_instance(data_dict)
                except Exception as e:
                    logger.error(e)
                # instance = self.my_class.model.create_instance(self.data_path)
                logger.info("Instance created with pyomo")

                # logger.info(instance.pprint())
                action_handle = solver_manager.queue(instance, opt=optsolver)
                logger.debug("Solver queue created " + str(action_handle))
                action_handle_map[action_handle] = str(self.id)
                logger.debug("Action handle map: " + str(action_handle_map))
                start_time = time.time()
                logger.debug("Optimization starting time: " + str(start_time))

                logger.debug("pyro mip server "+str(pyro_mip_server.pid))

                ###retrieve the solutions
                for i in range(1):
                    this_action_handle = solver_manager.wait_any()
                    self.solved_name = action_handle_map[this_action_handle]
                    self.results = solver_manager.get_results(this_action_handle)

                start_time = time.time() - start_time
                logger.info("Time to run optimizer = " + str(start_time) + " sec.")
                if (self.results.solver.status == SolverStatus.ok) and (
                        self.results.solver.termination_condition == TerminationCondition.optimal):
                    # this is feasible and optimal
                    logger.info("Solver status and termination condition ok")
                    logger.debug("Results for " + self.solved_name + " with id: " + str(self.id))
                    logger.debug(self.results)
                    instance.solutions.load_from(self.results)
                    try:
                        my_dict = {}
                        for v in instance.component_objects(Var, active=True):
                            # logger.debug("Variable in the optimization: "+ str(v))
                            varobject = getattr(instance, str(v))
                            var_list = []
                            try:
                                # Try and add to the dictionary by key ref
                                for index in varobject:
                                    var_list.append(varobject[index].value)
                                my_dict[str(v)] = var_list
                            except Exception as e:
                                logger.error(e)
                                # Append new index to currently existing items
                                # my_dict = {**my_dict, **{v: list}}

                        self.output.publishController(self.id, my_dict)
                    except Exception as e:
                        logger.error(e)
                elif self.results.solver.termination_condition == TerminationCondition.infeasible:
                    # do something about it? or exit?
                    logger.info("Termination condition is infeasible")
                else:
                    logger.info("Nothing fits")

                count += 1
                if self.repetition > 0 and count >= self.repetition:
                    break

                logger.info("Optimization thread going to sleep for " + str(self.control_frequency) + " seconds")
                time_spent = self.update_count()
                for i in range(self.control_frequency - time_spent):
                    time.sleep(1)
                    if self.stopRequest.isSet():
                        break
        except Exception as e:
            logger.error(e)
            e = str(e)
            solver_error = "The SolverFactory was unable to create the solver"
            if solver_error in e:
                i = e.index(solver_error)
                i_start = e.index("\"", i)
                i_end = e.index("\"", i_start + 1)
                solver = e[i_start + 1: i_end]
                return_msg = "Incorrect solver " + str(solver) + " used"
            else:
                return_msg = e
        finally:
            # Closing the pyomo servers
            logger.debug("Deactivating pyro servers")
            solver_manager.deactivate()
            logger.debug("Pyro servers deactivated: " + str(solver_manager))
            pyro_mip_server.kill()
            logger.debug("Exit pyro-mip-server server")

            # If Stop signal arrives it tries to disconnect all mqtt clients
            for key, object in self.output.mqtt.items():
                object.MQTTExit()
                logger.debug("Client " + key + " is being disconnected")

            logger.error(return_msg)
            self.finish_status = True
            return return_msg
