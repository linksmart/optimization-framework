import connexion
# import six
import logging
import configparser

from swagger_server.models.start import Start  # noqa: E501
# from swagger_server import util
from flask import json

# from optparse import OptionParser
from optimization.controller import OptController
import os
import time

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

def getFilePath(dir,file_name):
    #print(os.path.sep)
    #print(os.environ.get("HOME"))
    project_dir = os.path.dirname(os.path.realpath(__file__))
    #data_file = os.path.join("/usr/src/app",dir,file_name)
    data_file = os.path.join(dir, file_name)
    return data_file


def get_data_json(json_text, key):
    data = json.dumps(json_text)
    data2 = json.loads(data)
    return data2[key]


def framework_start(startOFW):  # noqa: E501
    """Command for starting the framework

     # noqa: E501

    :param json_request: Start command for the optimization framework
    :type json_request: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        logger.info("URL JSON received")
        # json_request = Start.from_dict(connexion.request.get_json())

        try:
            repetition = get_data_json(startOFW, "repetition")
            time_step = get_data_json(startOFW, "time_step")
            horizon = get_data_json(startOFW, "horizon")
            model_name = get_data_json(startOFW, "model_name")
            logger.info("Number of repetitions: " + str(repetition))
            logger.info("Output with the following time steps: " + str(time_step))
            logger.info("Optimization calculated with the following horizon: " + str(horizon))
            logger.info("Optimization calculated with the following model: " + model_name)

            # Creating an object of the configuration file
            config = configparser.RawConfigParser()
            config.read(getFilePath("utils", "ConfigFile.properties"))
            model_name = config.get("SolverSection", "model.name")
            logger.info("This is the solver name: "+model_name)
            model_path = os.path.join(config.get("SolverSection", "model.base.path"), model_name)+".py"

            # Taking the data file name from the configuration file
            data_file_name = config.get("SolverSection", "data.file")
            data_path = getFilePath("optimization", data_file_name)

            # Taking
            solver_name = config.get("SolverSection", "solver.name")

            opt = OptController("obj1", solver_name, data_path, model_path)

            while True:
                results = opt.start()
                logger.info(results)
                time.sleep(20)

        except Exception as e:
            logger.error(e)
    else:
        logger.error("Wrong Content-Type")
    return 'System started successfully'


def framework_stop():  # noqa: E501
    """Command for stoping the framework

     # noqa: E501


    :rtype: None
    """

    try:
        logger.info("Stopping the system")
        message = "System stopped succesfully"
    except Exception as e:
        logger.error(e)
        message = "Error stoping the system"
    return message
