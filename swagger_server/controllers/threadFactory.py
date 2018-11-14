import os
import logging
import configparser
import json

from IO.inputConfigParser import InputConfigParser
from IO.redisDB import RedisDB
from optimization.controller import OptController
from prediction.loadPrediction import LoadPrediction
from prediction.pvPrediction import PVPrediction
import subprocess

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class ThreadFactory:

    def __init__(self, model_name, control_frequency, horizon_in_steps, dT_in_seconds, repetition, solver, id):
        self.model_name = model_name
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.repetition = repetition
        self.solver = solver
        self.id = id
        self.redisDB = RedisDB()

    def getFilePath(self, dir, file_name):
        # print(os.path.sep)
        # print(os.environ.get("HOME"))
        project_dir = os.path.dirname(os.path.realpath(__file__))
        data_file = os.path.join("/usr/src/app", dir, file_name)
        return data_file

    def startOptControllerThread(self):
        logger.info("Creating optimization controller thread")
        logger.info("Number of repetitions: " + str(self.repetition))
        logger.info("Output with the following control_frequency: " + str(self.control_frequency))
        logger.info("Optimization calculated with the following horizon_in_steps: " + str(self.horizon_in_steps))
        logger.info("Optimization calculated with the following dT_in_seconds: " + str(self.dT_in_seconds))
        logger.info("Optimization calculated with the following model: " + self.model_name)
        logger.info("Optimization calculated with the following solver: " + self.solver)

        # Creating an object of the configuration file (standard values)
        try:
            config = configparser.RawConfigParser()
            config.read(self.getFilePath("utils", "ConfigFile.properties"))
        except Exception as e:
            logger.error(e)

        # Loads the solver name if it was not given thorough the endpoint command/start/id
        if not self.model_name:
            self.model_name = config.get("SolverSection", "model.name")
        logger.debug("This is the model name: " + self.model_name)
        self.model_path = os.path.join(config.get("SolverSection", "model.base.path"), self.model_name) + ".py"
        logger.debug("This is the path of the model: " + str(self.model_path))

        # Loads the solver name if not specified in command/start/id
        if not self.solver:
            self.solver_name = config.get("SolverSection", "solver.name")
        else:
            self.solver_name = self.solver
        logger.debug("Optimization calculated with the following solver: " + self.solver_name)

        ##############################################################################################
        output_config = None
        try:
            # Reads the registry/output and stores it into an object
            path = os.path.join(os.getcwd(), "utils", str(self.id), "Output.registry.mqtt")
            if not os.path.exists(path):
                logger.debug("Output.registry.mqtt not set, only file output available")
            else:
                with open(path, "r") as file:
                    output_config = json.loads(file.read())
        except Exception as e:
            logger.error("Output.registry.mqtt not set, only file output available")

        try:
            # Reads the registry/input and stores it into an object
            path = os.path.join(os.getcwd(), "utils", str(self.id), "Input.registry.file")
            if not os.path.exists(path):
                input_config_file = {}
                logger.debug("Not Input.registry.file present")
            else:
                with open(path, "r") as file:
                    input_config_file = json.loads(file.read())
                logger.debug("Input.registry.file found")
        except Exception as e:
            logger.error("Input file not found")
            input_config_file = {}
            logger.error(e)

        try:
            # Reads the registry/input and stores it into an object
            path = os.path.join(os.getcwd(), "utils", str(self.id), "Input.registry.mqtt")
            if not os.path.exists(path):
                input_config_mqtt = {}
                logger.debug("Not Input.registry.mqtt present")
            else:
                with open(path, "r") as file:
                    input_config_mqtt = json.loads(file.read())
                logger.debug("Input.registry.mqtt found")
        except Exception as e:
            logger.error("Input file not found")
            input_config_mqtt = {}
            logger.error(e)

        input_config_parser = InputConfigParser(input_config_file, input_config_mqtt, self.model_name)
        self.prediction_threads = {}
        self.prediction_names = input_config_parser.get_prediction_names()
        if self.prediction_names is not None and len(self.prediction_names) > 0:
            for prediction_name in self.prediction_names:
                flag = input_config_parser.get_forecast_flag(prediction_name)
                if flag:
                    logger.info("Creating prediction controller thread for topic " + str(prediction_name))
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
                        self.non_prediction_threads[non_prediction_name] = PVPrediction(config, input_config_parser, self.id,
                                                                                        self.control_frequency, self.horizon_in_steps,
                                                                                        self.dT_in_seconds)

        #initializes the name server and dispatcher server for pyomo
        try:
            self.name_server = subprocess.Popen(["/usr/local/bin/pyomo_ns"])
            logger.debug("Name server started: " + str(self.name_server))
            self.dispatch_server = subprocess.Popen(["/usr/local/bin/dispatch_srvr"])
            logger.debug("Dispatch server started: " + str(self.dispatch_server))
        except Exception as e:
            logger.error("new name server error, " + str(e))

        # Initializing constructor of the optimization controller thread
        self.opt = OptController(self.id, self.solver_name, self.model_path, self.control_frequency,
                                 self.repetition, output_config, input_config_parser, config, self.horizon_in_steps,
                                 self.dT_in_seconds, self.name_server,self.dispatch_server)

        ####starts the optimization controller thread
        try:
            self.opt.start()
        except Exception as e:
            logger.error(e)
        logger.debug("Optimization object started")

    def stopOptControllerThread(self):
        try:
            # stop as per ID
            for name, obj in self.prediction_threads.items():
                obj.Stop()
            for name, obj in self.non_prediction_threads.items():
                obj.Stop()
            logger.info("Stopping optimization controller thread")
            self.opt.Stop(self.id)
            logger.info("Optimization controller thread stopped")
            self.name_server.kill()
            logger.debug("Exit name server")
            self.dispatch_server.kill()
            logger.debug("Exit dispatch server")
            return "Optimization controller thread stopped"
        except Exception as e:
            logger.error(e)
            return e

    def is_running(self):
        return not self.opt.finish_status
