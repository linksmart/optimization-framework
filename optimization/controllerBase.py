"""
Created on Apr 24 16:10 2019

@author: nishit
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

from IO.MQTTClient import InvalidMQTTHostException
from pyutilib.pyro import shutdown_pyro_components

from IO.inputController import InputController
from IO.outputController import OutputController
from IO.redisDB import RedisDB
from optimization.ModelException import InvalidModelException
from threading import Event


import pyutilib.subprocess.GlobalData

from utils_intern.messageLogger import MessageLogger

pyutilib.subprocess.GlobalData.DEFINE_SIGNAL_HANDLERS_DEFAULT = False

from abc import ABC, abstractmethod


class ControllerBase(ABC, threading.Thread):

    def __init__(self, id, solver_name, model_path, control_frequency, repetition, output_config, input_config_parser,
                 config, horizon_in_steps, dT_in_seconds, optimization_type):
        # threading.Thread.__init__(self)
        super(ControllerBase, self).__init__()
        self.logger = MessageLogger.get_logger(__file__, id)
        self.logger.info("Initializing optimization controller " + id)
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
        self.redisDB = RedisDB()
        self.lock_key = "id_lock"
        self.optimization_type = optimization_type
        self.stop_signal_key = "opt_stop_" + self.id
        self.finish_status_key = "finish_status_" + self.id
        self.redisDB.set(self.stop_signal_key, False)
        self.redisDB.set(self.finish_status_key, False)
        self.repetition_completed = False
        self.preprocess = False

        try:
            # dynamic load of a class
            self.logger.info("This is the model path: " + self.model_path)
            module = self.path_import2(self.model_path)
            self.logger.info(getattr(module, 'Model'))
            self.my_class = getattr(module, 'Model')

        except Exception as e:
            self.logger.error(e)
            raise InvalidModelException("model is invalid/contains python syntax errors")

        if "False" in self.redisDB.get("Error mqtt" + self.id):
            self.output = OutputController(self.id, self.output_config)
        if "False" in self.redisDB.get("Error mqtt" + self.id):
            self.input = InputController(self.id, self.input_config_parser, config, self.control_frequency,
                                         self.horizon_in_steps, self.dT_in_seconds)

    # Importint a class dynamically
    def path_import2(self, absolute_path):
        spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
        module = spec.loader.load_module(spec.name)
        return module

    def join(self, timeout=None):
        self.stopRequest.set()
        super(ControllerBase, self).join(timeout)

    def Stop(self):
        try:
            self.input.Stop()
        except Exception as e:
            self.logger.error("error stopping input " + str(e))
        try:
            self.output.Stop()
        except Exception as e:
            self.logger.error("error stopping output " + str(e))
        self.redisDB.set(self.stop_signal_key, True)
        if self.isAlive():
            self.join(1)

    def update_count(self):
        st = time.time()
        if self.repetition > 0:
            path = "/usr/src/app/optimization/resources/ids_status.txt"
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
                    self.logger.error("error updating count in file " + str(e))
                finally:
                    self.redisDB.release_lock(self.lock_key, self.id)
        st = int(time.time() - st)
        return st

    # Start the optimization process and gives back a result
    def run(self):
        self.logger.info("Starting optimization controller")
        solver_manager = None
        return_msg = "success"
        try:
            ###maps action handles to instances
            action_handle_map = {}

            #####create a solver
            optsolver = SolverFactory(self.solver_name)
            self.logger.debug("Solver factory: " + str(optsolver))
            # optsolver.options["max_iter"]=5000
            self.logger.info("solver instantiated with " + self.solver_name)

            ###create a solver manager
            solver_manager = SolverManagerFactory('pyro')

            if solver_manager is None:
                self.logger.error("Failed to create a solver manager")
            else:
                self.logger.debug("Solver manager created: " + str(solver_manager) + str(type(solver_manager)))

            # self.logger.info("Solvers ipopt = "+ str(SolverFactory('ipopt').available()))
            # self.logger.info("Solvers glpk = "+ str(SolverFactory('glpk').available()))
            # self.logger.info("Solvers gurobi = " + str(SolverFactory('gurobi').available()))

            count = 0
            self.logger.info("This is the id: " + self.id)
            self.optimize(action_handle_map, count, optsolver, solver_manager)
        except Exception as e:
            self.logger.error(e)
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
            self.logger.info("thread stop event "+ str(self.stopRequest.isSet()))
            self.logger.info("repetition completed "+ str(self.repetition_completed))
            self.logger.info("stop request "+str(self.redisDB.get_bool(self.stop_signal_key)))
            if not self.redisDB.get_bool(self.stop_signal_key) and not self.repetition_completed:
                self.logger.error("Process interrupted")
                self.redisDB.set("kill_signal", True)
            self.logger.debug("Deactivating pyro servers")
            # TODO : 'SolverManager_Pyro' object has no attribute 'deactivate'
            # this error was not present before pyomo update
            # solver_manager.deactivate()
            self.logger.debug("Pyro servers deactivated: " + str(solver_manager))

            # If Stop signal arrives it tries to disconnect all mqtt clients
            for key, object in self.output.mqtt.items():
                object.MQTTExit()
                self.logger.debug("Client " + key + " is being disconnected")

            self.logger.info(return_msg)
            self.redisDB.set(self.finish_status_key, True)
            return return_msg

    @abstractmethod
    def optimize(self, action_handle_map, count, optsolver, solver_manager):
        while not self.redisDB.get_bool(self.stop_signal_key):
            pass

    def get_finish_status(self):
        return self.redisDB.get_bool(self.finish_status_key)
