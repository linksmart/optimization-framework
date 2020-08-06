import os
import configparser
import json

import time

from IO.inputConfigParser import InputConfigParser
from IO.redisDB import RedisDB
from optimization.ModelException import MissingKeysException
from optimization.controllerDiscrete import OptControllerDiscrete
from optimization.controllerMpc import OptControllerMPC
from optimization.controllerStochasticTestMulti import OptControllerStochastic
#from optimization.controllerStochasticTestPebble import OptControllerStochastic
from prediction.machineLearning import MachineLearning
from prediction.prediction import Prediction
from prediction.pvPrediction import PVPrediction
from utils_intern.constants import Constants
from utils_intern.messageLogger import MessageLogger


class ThreadFactory:

    def __init__(self, model_name, control_frequency, horizon_in_steps, dT_in_seconds, repetition, solver, id,
                 optimization_type, single_ev, restart):
        self.id = id
        self.logger = MessageLogger.get_logger(__name__, id)
        self.model_name = model_name
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.repetition = repetition
        self.solver = solver
        self.optimization_type = optimization_type
        self.single_ev = single_ev
        self.redisDB = RedisDB()
        self.pyro_mip_server = None
        #restart = True
        self.restart = restart

    def getFilePath(self, dir, file_name):
        # print(os.path.sep)
        # print(os.environ.get("HOME"))
        project_dir = os.path.dirname(os.path.realpath(__file__))
        data_file = os.path.join("/usr/src/app", dir, file_name)
        return data_file

    def startOptControllerThread(self):
        self.logger.info("Creating optimization controller thread")
        self.logger.info("Number of repetitions: " + str(self.repetition))
        self.logger.info("Output with the following control_frequency: " + str(self.control_frequency))
        self.logger.info("Optimization calculated with the following horizon_in_steps: " + str(self.horizon_in_steps))
        self.logger.info("Optimization calculated with the following dT_in_seconds: " + str(self.dT_in_seconds))
        self.logger.info("Optimization calculated with the following model: " + self.model_name)
        self.logger.info("Optimization calculated with the following solver: " + self.solver)
        self.logger.info("Optimization calculated with the following optimization_type: " + self.optimization_type)

        self.redisDB.set("Error mqtt" + self.id, False)
        #self.logger.debug("Error mqtt " + str(self.redisDB.get("Error mqtt" + self.id)))

        # Creating an object of the configuration file (standard values)
        try:
            config = configparser.RawConfigParser()
            config.read(self.getFilePath("optimization/resources", "ConfigFile.properties"))
        except Exception as e:
            self.logger.error(e)

        # Loads the solver name if it was not given thorough the endpoint command/start/id
        if not self.model_name:
            self.model_name = config.get("SolverSection", "model.name")
        self.logger.debug("This is the model name: " + self.model_name)
        self.model_path = os.path.join(config.get("SolverSection", "model.base.path"), self.model_name) + ".py"
        self.logger.debug("This is the path of the model: " + str(self.model_path))

        # Loads the solver name if not specified in command/start/id
        if not self.solver:
            self.solver_name = config.get("SolverSection", "solver.name")
        else:
            self.solver_name = self.solver
        self.logger.debug("Optimization calculated with the following solver: " + self.solver_name)

        ##############################################################################################
        output_config = None
        try:
            # Reads the registry/output and stores it into an object
            path = os.path.join(os.getcwd(), "optimization/resources", str(self.id), "Output.registry.mqtt")
            if not os.path.exists(path):
                self.logger.debug("Output.registry.mqtt not set, only file output available")
            else:
                with open(path, "r") as file:
                    output_config = json.loads(file.read())
        except Exception as e:
            self.logger.error("Output.registry.mqtt not set, only file output available")

        try:
            # Reads the registry/input and stores it into an object
            path = os.path.join(os.getcwd(), "optimization/resources", str(self.id), "Input.registry")
            if not os.path.exists(path):
                input_config = {}
                self.logger.debug("Not Input.registry.file present")
            else:
                with open(path, "r") as file:
                    input_config = json.loads(file.read())
                self.logger.debug("Input.registry.file found")
        except Exception as e:
            self.logger.error("Input file not found")
            input_config = {}
            self.logger.error(e)

        persist_base_path = config.get("IO", "persist.base.file.path")
        persist_base_path = os.path.join(os.getcwd(), persist_base_path, str(self.id), Constants.persisted_folder_name)
        input_config_parser = InputConfigParser(input_config, self.model_name, self.id, self.optimization_type,
                                                self.dT_in_seconds, self.horizon_in_steps,
                                                persist_base_path, self.restart)

        missing_keys = input_config_parser.check_keys_for_completeness()
        if len(missing_keys) > 0:
            raise MissingKeysException("Data source for following keys not declared: " + str(missing_keys))

        opt_values = input_config_parser.get_optimization_values()
        self.redisDB.set(self.id+":opt_values", json.dumps(opt_values))

        self.prediction_threads = {}
        self.pv_prediction_threads = {}
        for indexed_name, value in input_config_parser.name_params.items():
            if "mqtt" in value.keys():
                name = indexed_name[0]
                index = indexed_name[1]
                name_with_index = name + "~" + str(index)
                params = value["mqtt"]
                option = params["option"]
                if option == "predict":
                    self.logger.info("Creating prediction controller thread for topic " + str(name_with_index))
                    parameters = json.dumps(
                        {"control_frequency": self.control_frequency, "horizon_in_steps": self.horizon_in_steps,
                         "topic_param": params, "dT_in_seconds": self.dT_in_seconds, "type": "load"})
                    self.redisDB.set("train:" + self.id + ":" + name_with_index, parameters)
                    self.prediction_threads[indexed_name] = Prediction(config, self.control_frequency,
                                                                              self.horizon_in_steps, name_with_index,
                                                                              params, self.dT_in_seconds, self.id,
                                                                             output_config, "load", opt_values)
                    self.prediction_threads[indexed_name].start()
                elif option == "pv_predict":
                    self.pv_prediction_threads[indexed_name] = PVPrediction(config, output_config,
                                                                                  input_config_parser,
                                                                                  self.id,
                                                                                  self.control_frequency,
                                                                                  self.horizon_in_steps,
                                                                                  self.dT_in_seconds,
                                                                                  params,
                                                                                  name_with_index, index)
                    self.pv_prediction_threads[indexed_name].start()
                elif option == "pv_predict_lstm":
                    self.logger.info("Creating prediction controller thread for topic " + str(name_with_index))
                    parameters = json.dumps(
                        {"control_frequency": self.control_frequency, "horizon_in_steps": self.horizon_in_steps,
                         "topic_param": params, "dT_in_seconds": self.dT_in_seconds, "type": "pv"})
                    self.redisDB.set("train:" + self.id + ":" + name_with_index, parameters)
                    self.prediction_threads[indexed_name] = Prediction(config, self.control_frequency,
                                                                       self.horizon_in_steps, name_with_index,
                                                                       params, self.dT_in_seconds, self.id,
                                                                       output_config, "pv", opt_values)
                    self.prediction_threads[indexed_name].start()


        # Initializing constructor of the optimization controller thread
        if self.optimization_type == "MPC":
            self.opt = OptControllerMPC(self.id, self.solver_name, self.model_path, self.control_frequency,
                                        self.repetition, output_config, input_config_parser, config,
                                        self.horizon_in_steps,
                                        self.dT_in_seconds, self.optimization_type)
        elif self.optimization_type == "discrete":
            self.opt = OptControllerDiscrete(self.id, self.solver_name, self.model_path, self.control_frequency,
                                             self.repetition, output_config, input_config_parser, config,
                                             self.horizon_in_steps,
                                             self.dT_in_seconds, self.optimization_type)
        elif self.optimization_type == "stochastic":
            self.opt = OptControllerStochastic(self.id, self.solver_name, self.model_path,
                                                          self.control_frequency, self.repetition, output_config,
                                                          input_config_parser, config, self.horizon_in_steps,
                                                          self.dT_in_seconds, self.optimization_type, self.single_ev)

        try:
            ####starts the optimization controller thread
            self.logger.debug("Mqtt issue " + str(self.redisDB.get("Error mqtt" + self.id)))
            if "False" in self.redisDB.get("Error mqtt" + self.id):
                self.opt.start()
                self.logger.debug("Optimization object started")
                return 0
            else:
                self.redisDB.set("run:" + self.id, "stopping")
                self.stopOptControllerThread()
                self.redisDB.set("run:" + self.id, "stopped")
                self.logger.error("Optimization object could not be started")
                return 2
        except Exception as e:
            self.logger.error(e)
            return 1

    def stopOptControllerThread(self):
        try:
            # stop as per ID
            for name, obj in self.prediction_threads.items():
                self.redisDB.remove("train:" + self.id + ":" + name)
                obj.Stop()
            for name, obj in self.pv_prediction_threads.items():
                obj.Stop()
            self.logger.info("Stopping optimization controller thread")
            self.opt.Stop()
            self.logger.info("Optimization controller thread stopped")
            return "Optimization controller thread stopped"
        except Exception as e:
            self.logger.error(e)
            return e

    def is_running(self):
        return not self.opt.get_finish_status()

    def update_training_params(self, key, parameters):
        while True:
            self.redisDB.set(key, parameters)
            time.sleep("60")
