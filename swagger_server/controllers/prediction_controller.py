"""
Created on Jul 10 12:24 2018

@author: nishit
"""
import logging

import connexion
from swagger_server.models.start_predict import StartPredict  # noqa: E501

from swagger_server.controllers.threadFactory import ThreadFactory

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class PredictionController:

    factory=None
    running=False

    def set(self, object):
        self.factory=object

    def get(self):
        return self.factory

    def set_isRunning(self, bool):
        self.running = bool

    def get_isRunning(self):
        return self.running

    def start(self, json_object):
        self.predict = json_object.predict

        self.set(ThreadFactory())

        logger.info("Thread: " + str(self.get()))
        self.get().startLoadPredictionThread()
        self.set_isRunning(True)

    def stop(self):
        logger.debug("Stop signal received")
        logger.debug("This is the factory object: "+str(self.get()))
        if self.factory:
            self.factory.stopLoadPredictionThread()
            self.set_isRunning(False)
            message = "System stopped succesfully"
            logger.debug(message)
        else:
            message="No threads found"
            logger.debug(message)

variable=PredictionController()


def framework_start(startPred):  # noqa: E501
    """Command for starting the prediction thread

    # noqa: E501

    :param startOFW: Start command for the optimization framework
    :type startOFW: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        logger.info("Starting the system")
        startPred = StartPredict.from_dict(connexion.request.get_json())

        if not variable.get_isRunning():
            variable.start(startPred)
        else:
            logger.debug("System already running")

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
        if variable.get_isRunning():
            logger.debug("System running and trying to stop")
            variable.stop()
            message="System stopped succesfully"
        else:
            logger.debug("System already stopped")
            message = "System already stopped"

    except Exception as e:
        logger.error(e)
        message = "Error stoping the system"
    return message

