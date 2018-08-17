
import os
import logging
import configparser
import json

from IO.inputConfigParser import InputConfigParser
from mock_data.mockGenericDataPublisher import MockGenericDataPublisher
from mock_data.mockSoCDataPublisher import MockSoCDataPublisher
from optimization.controller import OptController
from mock_data.mockPLoadDataPublisher import MockPLoadDataPublisher
from prediction.loadPrediction import LoadPrediction
from prediction.pvPrediction import PVPrediction

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class ThreadFactory:

    def __init__(self, model_name, time_step, horizon, repetition, solver, id):
        self.model_name=model_name
        self.time_step=time_step
        self.horizon=horizon
        self.repetition=repetition
        self.solver=solver
        self.id = id


    def getFilePath(self,dir, file_name):
        # print(os.path.sep)
        # print(os.environ.get("HOME"))
        project_dir = os.path.dirname(os.path.realpath(__file__))
        data_file = os.path.join("/usr/src/app", dir, file_name)
        return data_file

    def startOptControllerThread(self):
        logger.info("Creating optimization controller thread")
        logger.info("Number of repetitions: " + str(self.repetition))
        logger.info("Output with the following time steps: " + str(self.time_step))
        logger.info("Optimization calculated with the following horizon: " + str(self.horizon))
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
            with open(path, "r") as file:
                output_config = json.loads(file.read())
        except Exception as e:
            logger.error("Output.registry.mqtt not set, only file output available")

        try:
            # Reads the registry/input and stores it into an object
            path = os.path.join(os.getcwd(), "utils", str(self.id),"Input.registry.file")
            with open(path, "r") as file:
                input_config_file = json.loads(file.read())
        except Exception as e:
            logger.error("Input file not found")
            input_config_file = {}
            logger.error(e)

        try:
            # Reads the registry/input and stores it into an object
            path = os.path.join(os.getcwd(), "utils", str(self.id),"Input.registry.mqtt")
            with open(path, "r") as file:
                input_config_mqtt = json.loads(file.read())
        except Exception as e:
            logger.error("Input file not found")
            input_config_mqtt = {}
            logger.error(e)

        input_config_parser = InputConfigParser(input_config_file, input_config_mqtt)

        """Need to get data from config or input.registry?"""
        self.pv_forecast = input_config_parser.get_forecast_flag("P_PV")
        if self.pv_forecast:
            self.pv_prediction = PVPrediction(config, input_config_parser)

        self.load_forecast = input_config_parser.get_forecast_flag("P_Load")
        if self.load_forecast:
            logger.info("Creating load prediction controller thread")
            # Creating an object of the configuration file
            config = configparser.RawConfigParser()
            config.read(self.getFilePath("utils", "ConfigFile.properties"))
            self.load_prediction = LoadPrediction(config, input_config_parser, self.time_step, self.horizon)
            self.load_prediction.start()

        logger.debug("Start in threadfactory finished")

        # Initializing constructor of the optimization controller thread
        self.opt = OptController(self.id, self.solver_name, self.model_path, self.time_step,
                                 self.repetition, output_config, input_config_parser, config)
        ####starts the optimization controller thread
        try:
            self.opt.start()
        except Exception as e:
            logger.error(e)
        logger.debug("Optimization object started")

    def stopOptControllerThread(self):
        try:
            # stop as per ID
            if self.load_forecast:
                logger.info("Stopping load thread")
                self.load_prediction.Stop()
            if self.pv_forecast:
                logger.info("Stopping pv thread")
                self.pv_prediction.Stop()
            logger.info("Stopping optimization controller thread")
            self.opt.Stop(self.id)
            logger.info("Optimization controller thread stopped")
            return "Optimization controller thread stopped"
        except Exception as e:
            logger.error(e)
            return e

    def is_running(self):
        return not self.opt.finish_status