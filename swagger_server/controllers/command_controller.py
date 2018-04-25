import connexion
import six
import logging


from swagger_server.models.start import Start  # noqa: E501
from swagger_server import util
from flask import json
from swagger_server.controllers.threadFactory import ThreadFactory


import os, time

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class Object(object):

    optimizationObject=None

    def __init__(self):
        self.isThereObject=False




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
        startOFW = Start.from_dict(connexion.request.get_json())


        repetition = getDataJSON(startOFW,"repetition")
        time_step= getDataJSON(startOFW,"time_step")
        horizon = getDataJSON(startOFW, "horizon")
        model_name = getDataJSON(startOFW,"model_name")

        factory = ThreadFactory(model_name, time_step, horizon, repetition)
        Object.optimizationObject=factory
        Object.isThereObject=True
        logger.info("Thread: "+str(factory))
        factory.startOptControllerThread()
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
        if Object.isThereObject is True:
            Object.optimizationObject.stopOptControllerThread()
            Object.isThereObject = False
            message = "System stopped succesfully"
            logger.info(message)
        else:
            message="No threads found"
            logger.info(message)
    except Exception as e:
        logger.error(e)
        message = "Error stoping the system"
    return message
