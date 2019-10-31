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
#from pyomo.util.plugin import *
from pyomo.opt.parallel.manager import *
import pyomo.solvers.plugins.smanager.pyro

from pyutilib.services import TempfileManager
#TempfileManager.tempdir = "/usr/src/app/logs/pyomo"
import time
import shutil

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
        super().__init__()

        pyomo_path = "/usr/src/app/logs/pyomo_" + str(id)
        if not os.path.exists(pyomo_path):
            os.makedirs(pyomo_path, mode=0o777, exist_ok=False)
            os.chmod(pyomo_path, 0o777)
        TempfileManager.tempdir = pyomo_path

        self.logger = MessageLogger.get_logger(__name__, id)
        self.logger.info("Initializing optimization controller " + id)
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
        self.stopRequest = None#threading.Event()
        self.redisDB = RedisDB()
        self.lock_key = "id_lock"
        self.optimization_type = optimization_type
        self.stop_signal_key = "opt_stop_" + self.id
        self.finish_status_key = "finish_status_" + self.id
        self.redisDB.set(self.stop_signal_key, False)
        self.redisDB.set(self.finish_status_key, False)
        self.repetition_completed = False
        self.preprocess = False
        self.input = None
        self.output = None
        if "False" in self.redisDB.get("Error mqtt" + self.id):
            self.output = OutputController(self.id, self.output_config)
        if "False" in self.redisDB.get("Error mqtt" + self.id):
            self.input = InputController(self.id, self.input_config_parser, config, self.control_frequency,
                                         self.horizon_in_steps, self.dT_in_seconds)
        """try:
            # dynamic load of a class
            self.logger.info("This is the model path: " + self.model_path)
            module = self.path_import2(self.model_path)
            self.logger.info(getattr(module, 'Model'))
            self.my_class = getattr(module, 'Model')

        except Exception as e:
            self.logger.error(e)
            raise InvalidModelException("model is invalid/contains python syntax errors")"""



    # Importint a class dynamically
    def path_import2(self, absolute_path):
        spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
        module = spec.loader.load_module(spec.name)
        return module

    def join(self, timeout=None):
        #self.stopRequest.set()
        super(ControllerBase, self).join(timeout)

    def Stop(self):
        try:
            if self.input:
                self.input.Stop()
                self.logger.debug("Deleting input instances")
                #del self.input.inputPreprocess
                #del self.input
        except Exception as e:
            self.logger.error("error stopping input " + str(e))
        try:
            if self.output:
                self.output.Stop()
                self.logger.debug("Deleting output instances")
                #del self.output
        except Exception as e:
            self.logger.error("error stopping output " + str(e))

        #erasing files from pyomo
        #self.erase_pyomo_files()
        self.logger.debug("setting stop_signal_key")
        self.redisDB.set(self.stop_signal_key, True)

        if self.isAlive():
            self.join(1)

    def initialize_opt_solver(self):
        start_time_total = time.time()

        self.optsolver = SolverFactory(self.solver_name)#, tee=False, keepfiles=False, verbose=False, load_solutions=False)  # , solver_io="lp")
        #self.optsolver.verbose= False
        #self.optsolver.load_solutions = False
        self.logger.debug("Solver factory: " + str(self.optsolver))
        #self.optsolver.options.tee=False
        #self.optsolver.options.keepfiles = False
        #self.optsolver.options.load_solutions = False
        # optsolver.options["max_iter"]=5000
        self.logger.info("solver instantiated with " + self.solver_name)
        #return self.optsolver

    def initialize_solver_manager(self):
        ###create a solver manager
        self.solver_manager = None
        #self.solver_manager = SolverManagerFactory('pyro', host='localhost')
        self.logger.debug("Starting the solver_manager")
        #return self.solver_manager
        # optsolver.options.pyro_shutdown = True

    def erase_pyomo_files(self, folder):
        # erasing files from pyomo
        #folder = "/usr/src/app/logs/pyomo"
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                # elif os.path.isdir(file_path): shutil.rmtree(file_path)
            except Exception as e:
                self.logger.error(e)


    # Start the optimization process and gives back a result
    def run(self):
        self.logger.info("Starting optimization controller")

        return_msg = "success"
        execution_error = False
        try:

            count = 0

            self.optimize(count, self.solver_name, self.model_path)

        except Exception as e:
            execution_error = True
            self.logger.error("error overall "+ str(e))
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

            self.logger.info("repetition completed "+ str(self.repetition_completed))
            self.logger.info("stop request "+str(self.redisDB.get_bool(self.stop_signal_key)))
            self.logger.info("execution error "+str(execution_error))
            if not self.redisDB.get_bool(self.stop_signal_key) and not self.repetition_completed and not execution_error:
                self.logger.error("Process interrupted")
                self.redisDB.set("kill_signal", True)

            #erase pyomo folder
            folder = "/usr/src/app/logs/pyomo_" + str(self.id)
            shutil.rmtree(folder, ignore_errors=True)

            # If Stop signal arrives it tries to disconnect all mqtt clients
            if self.output:
                for key, object in self.output.mqtt.items():
                    object.MQTTExit()
                    self.logger.debug("Client " + key + " is being disconnected")

            self.logger.info(return_msg)
            self.redisDB.set(self.finish_status_key, True)
            return return_msg

    @abstractmethod
    def optimize(self, count, solver_name, model_path):
        while not self.redisDB.get_bool(self.stop_signal_key):
            pass

    def get_finish_status(self):
        return self.redisDB.get_bool(self.finish_status_key)
