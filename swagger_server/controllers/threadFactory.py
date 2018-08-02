
import os
import logging
import configparser
import json

from optimization.controller import OptController
from optimization.loadForecastPublisher import LoadForecastPublisher
from optimization.pvForecastPublisher import PVForecastPublisher
from prediction.mockDataPublisher import MockDataPublisher
from prediction.loadPrediction import LoadPrediction

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class ThreadFactory:

    def __init__(self, model_name, time_step, horizon, repetition, solver):
        self.model_name=model_name
        self.time_step=time_step
        self.horizon=horizon
        self.repetition=repetition
        self.solver=solver


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

        # Creating an object of the configuration file
        config = configparser.RawConfigParser()
        config.read(self.getFilePath("utils", "ConfigFile.properties"))
        if not self.model_name:
            self.model_name = config.get("SolverSection", "model.name")

        logger.debug("This is the model name: " + self.model_name)
        self.model_path = os.path.join(config.get("SolverSection", "model.base.path"), self.model_name) + ".py"
        logger.debug("This is the model name: " + str(self.model_path))
        # Taking the data file name from the configuration file
        data_file_name = config.get("SolverSection", "data.file")
        self.data_path = self.getFilePath("optimization", data_file_name)

        # Taking
        if not self.solver:
            self.solver_name = config.get("SolverSection", "solver.name")
        else:
            self.solver_name = self.solver

        logger.debug("Optimization calculated with the following solver: " + self.solver_name)
        ##############################################################################################
        # Reads the registry/output and stores it into an object
        path = self.getFilePath("utils", "Output.registry")
        with open(path, "r") as file:
            output_config = json.loads(file.read())
        #logger.debug("This is the output data: " + str(output_config))

        try:
            # Reads the registry/input and stores it into an object
            path = self.getFilePath("utils", "Input.registry")
            with open(path, "r") as file:
                input_config = json.loads(file.read())
        except Exception as e:
            logger.error("Input file not found")
            input_config = {}

        #Initializing constructor of the optimization controller thread
        self.opt = OptController("obj1", self.solver_name, self.data_path, self.model_path, self.time_step,
                                 self.repetition, output_config, input_config, config)
        ####starts the optimization controller thread
        results = self.opt.start()

        """Need to get data from config or input.registry?"""
        self.pv_forecast = True
        if "photovoltaic" in input_config.keys():
            self.pv_forecast = bool(input_config["photovoltaic"]["Internal_Forecast"])
        if self.pv_forecast:
            pv_forecast_topic = config.get("IO", "pv.forecast.topic")
            pv_forecast_topic = json.loads(pv_forecast_topic)
            self.pv_forecast_pub = PVForecastPublisher(pv_forecast_topic, config)
            self.pv_forecast_pub.start()

        """need to to be in a separate file?"""
        self.load_forecast = True

        if "load" in input_config.keys():
            self.load_forecast = bool(input_config["load"]["Internal_Forecast"])
        if self.load_forecast:
            raw_data_topic = config.get("IO", "raw.data.topic")
            raw_data_topic = json.loads(raw_data_topic)
            self.mock_data = MockDataPublisher(raw_data_topic, config)
            self.mock_data.start()
            logger.info("Creating load prediction controller thread")
            # Creating an object of the configuration file
            config = configparser.RawConfigParser()
            config.read(self.getFilePath("utils", "ConfigFile.properties"))
            self.load_prediction = LoadPrediction(config, self.time_step, self.horizon)
            self.load_prediction.start()


    def stopOptControllerThread(self):
        try:
            if self.load_forecast:
                logger.info("Stopping mock data thread")
                #self.mock_data.Stop()
                logger.info("Stopping load prediction thread")
                #self.load_prediction.Stop()
            if self.pv_forecast:
                logger.info("Stopping pv forecast thread")
                self.pv_forecast_pub.Stop()
            logger.info("Stopping optimization controller thread")
            self.opt.Stop()
            logger.info("Optimization controller thread stopped")
        except Exception as e:
            logger.error(e)

    def is_running(self):
        return not self.opt.finish_status