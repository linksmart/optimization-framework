
import os
import logging
import configparser
import json

from optimization.controller import OptController
from optimization.loadForecastPublisher import LoadForecastPublisher
from optimization.pvForecastPublisher import PVForecastPublisher
from prediction.loadController import LoadController
from prediction.mockDataPublisher import MockDataPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class ThreadFactory:

    def __init__(self, model_name, time_step, horizon, repetition):
        self.model_name=model_name
        self.time_step=time_step
        self.horizon=horizon
        self.repetition=repetition


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

        # Creating an object of the configuration file
        config = configparser.RawConfigParser()
        config.read(self.getFilePath("utils", "ConfigFile.properties"))
        self.model_name = config.get("SolverSection", "model.name")
        logger.info("This is the model name: " + self.model_name)
        self.model_path = os.path.join(config.get("SolverSection", "model.base.path"), self.model_name) + ".py"

        # Taking the data file name from the configuration file
        data_file_name = config.get("SolverSection", "data.file")
        self.data_path = self.getFilePath("optimization", data_file_name)

        # Taking
        self.solver_name = config.get("SolverSection", "solver.name")

        ##############################################################################################
        # Reads the registry/output and stores it into an object
        path = self.getFilePath("utils", "Output.registry")
        with open(path, "r") as file:
            output_config = json.loads(file.read())
        #logger.debug("This is the output data: " + str(output_config))

        #Initializing constructor of the optimization controller thread
        self.opt = OptController("obj1", self.solver_name, self.data_path, self.model_path, self.time_step, output_config, config)
        ####starts the optimization controller thread
        results = self.opt.start()

        """Need to get data from config or input.registry?"""


        pv_forecast_topic = config.get("IO", "pv.forecast.topic")
        pv_forecast_topic = json.loads(pv_forecast_topic)
        self.pv_forecast_pub = PVForecastPublisher(pv_forecast_topic, config)
        self.pv_forecast_pub.start()


        """need to to be in a separate file"""
        raw_data_topic = config.get("IO", "raw.data.topic")
        raw_data_topic = json.loads(raw_data_topic)
        self.mock_data = MockDataPublisher(raw_data_topic, config)
        self.mock_data.start()
        self.load_controller = LoadController(config)
        self.load_controller.start()

    def stopOptControllerThread(self):
        try:
            logger.info("Stopping mock data thread")
            self.mock_data.Stop()
            logger.info("Stopping load controller thread")
            self.load_controller.Stop()
            logger.info("Stopping pv forecast thread")
            self.pv_forecast_pub.Stop()
            logger.info("Stopping optimization controller thread")
            self.opt.Stop()
            logger.info("Optimization controller thread stopped")
        except Exception as e:
            logger.error(e)
