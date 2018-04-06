import connexion
import six
import logging
import configparser

from swagger_server.models.start import Start  # noqa: E501
from swagger_server import util
from flask import json

from optparse import OptionParser
from optimization.controller import OptController
import os, time

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

def getFilePath(dir,file_name):
    print(os.path.sep)
    print(os.environ.get("HOME"))
    project_dir = os.path.dirname(os.path.realpath(__file__))
    data_file = os.path.join("/usr/src/app",dir,file_name)
    return data_file

def getDataJSON(object, key):
    data=json.dumps(object)
    data2=json.loads(data)
    return data2[key]


def framework_start(startOFW):  # noqa: E501
    """Command for starting the framework

     # noqa: E501

    :param startOFW: Start command for the optimization framework
    :type startOFW: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        logger.info("URL JSON received")
        startOFW = Start.from_dict(connexion.request.get_json())  # noqa: E501

        try:
            frequency = getDataJSON(startOFW,"frequency")
            solverName= getDataJSON(startOFW,"solver_name")
            print("Frequency: "+str(frequency))
            print("Solver: "+solverName)

            # Creating an object of the configuration file
            config = configparser.RawConfigParser()
            print(getFilePath("utils","ConfigFile.properties"))
            config.read(getFilePath("utils","ConfigFile.properties"))
            print(config.sections())
            model_name = config.get("SolverSection", "model.name")

            # Taking the data file name from the configuration file
            data_file_name = config.get("SolverSection", "data.file")
            data_path = getFilePath("optimization",data_file_name)

            # Taking
            solver_name = config.get("SolverSection", "solver.name")
            print("Problem solved with: " + solver_name)

            opt = OptController("obj1", solver_name, data_path, model_name)

            while True:
                results = opt.start()
                logger.info(results)
                time.sleep(frequency)


        except Exception as e:
            logger.error(e)
    else:
        logger.error("Wrong Content-Type")
    return 'System started succesfully'


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
