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
from prediction.loadPrediction import LoadPrediction
from prediction.pvPrediction import PVPrediction
from utils_intern.messageLogger import MessageLogger


class ThreadFactory:

    def __init__(self, model_name, control_frequency, horizon_in_steps, dT_in_seconds, repetition, solver, id,
                 optimization_type, single_ev):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.model_name = model_name
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.repetition = repetition
        self.solver = solver
        self.id = id
        self.optimization_type = optimization_type
        self.single_ev = single_ev
        self.redisDB = RedisDB()
        self.pyro_mip_server = None

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
        self.logger.debug("Error mqtt " + str(self.redisDB.get("Error mqtt" + self.id)))

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
            path = os.path.join(os.getcwd(), "optimization/resources", str(self.id), "Input.registry.file")
            if not os.path.exists(path):
                input_config_file = {}
                self.logger.debug("Not Input.registry.file present")
            else:
                with open(path, "r") as file:
                    input_config_file = json.loads(file.read())
                self.logger.debug("Input.registry.file found")
        except Exception as e:
            self.logger.error("Input file not found")
            input_config_file = {}
            self.logger.error(e)

        try:
            # Reads the registry/input and stores it into an object
            path = os.path.join(os.getcwd(), "optimization/resources", str(self.id), "Input.registry.mqtt")
            if not os.path.exists(path):
                input_config_mqtt = {}
                self.logger.debug("Not Input.registry.mqtt present")
            else:
                with open(path, "r") as file:
                    input_config_mqtt = json.loads(file.read())
                self.logger.debug("Input.registry.mqtt found")
        except Exception as e:
            self.logger.error("Input file not found")
            input_config_mqtt = {}
            self.logger.error(e)

        input_config_parser = InputConfigParser(input_config_file, input_config_mqtt, self.model_name, self.id, self.optimization_type)

        missing_keys = input_config_parser.check_keys_for_completeness()
        if len(missing_keys) > 0:
            raise MissingKeysException("Data source for following keys not declared: " + str(missing_keys))

        self.prediction_threads = {}
        self.prediction_names = input_config_parser.get_prediction_names()
        if self.prediction_names is not None and len(self.prediction_names) > 0:
            for prediction_name in self.prediction_names:
                flag = input_config_parser.get_forecast_flag(prediction_name)
                if flag:
                    self.logger.info("Creating prediction controller thread for topic " + str(prediction_name))
                    topic_param = input_config_parser.get_params(prediction_name)
                    parameters = json.dumps(
                        {"control_frequency": self.control_frequency, "horizon_in_steps": self.horizon_in_steps,
                         "topic_param": topic_param, "dT_in_seconds": self.dT_in_seconds})
                    self.redisDB.set("train:" + self.id + ":" + prediction_name, parameters)
                    self.prediction_threads[prediction_name] = LoadPrediction(config, self.control_frequency,
                                                                              self.horizon_in_steps, prediction_name,
                                                                              topic_param, self.dT_in_seconds, self.id,
                                                                              True)
                    # self.prediction_threads[prediction_name].start()

        self.non_prediction_threads = {}
        self.non_prediction_names = input_config_parser.get_non_prediction_names()
        if self.non_prediction_names is not None and len(self.non_prediction_names) > 0:
            for non_prediction_name in self.non_prediction_names:
                flag = input_config_parser.get_forecast_flag(non_prediction_name)
                if flag:
                    if non_prediction_name == "P_PV":
                        self.non_prediction_threads[non_prediction_name] = PVPrediction(config, input_config_parser,
                                                                                        self.id,
                                                                                        self.control_frequency,
                                                                                        self.horizon_in_steps,
                                                                                        self.dT_in_seconds,
                                                                                        non_prediction_name)
                        self.non_prediction_threads[non_prediction_name].start()

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
                return 1
        except Exception as e:
            self.logger.error(e)
            return 1

    def stopOptControllerThread(self):
        try:
            # stop as per ID
            for name, obj in self.prediction_threads.items():
                self.redisDB.remove("train:" + self.id + ":" + name)
                obj.Stop()
            for name, obj in self.non_prediction_threads.items():
                obj.Stop()
                del obj
            self.logger.info("Stopping optimization controller thread")
            self.opt.Stop()
            del self.opt
            self.logger.info("Optimization controller thread stopped")
            del self.logger
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
