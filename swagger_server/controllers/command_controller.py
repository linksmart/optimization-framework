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


class CommandController:

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
        self.model_name = json_object.model_name
        self.time_step = json_object.time_step
        self.horizon = json_object.horizon
        self.repetition = json_object.repetition
        #logger.info("Self.factory "+str(self.factory))

        self.set(ThreadFactory(self.model_name, self.time_step, self.horizon, self.repetition))

        #logger.info("Self.factory 2 " + str(self.factory))
        logger.info("Thread: " + str(self.get()))
        self.get().startOptControllerThread()
        self.set_isRunning(True)

    def stop(self):
        logger.debug("Stop signal received")
        logger.debug("This is the factory object: "+str(self.get()))
        if self.factory:
            self.factory.stopOptControllerThread()
            self.set_isRunning(False)
            message = "System stopped succesfully"
            logger.debug(message)
        else:
            message="No threads found"
            logger.debug(message)

variable=CommandController()

def framework_start(startOFW):  # noqa: E501
    """Command for starting the framework

    # noqa: E501

    :param startOFW: Start command for the optimization framework
    :type startOFW: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        logger.info("Starting the system")
        startOFW = Start.from_dict(connexion.request.get_json())

        if not variable.get_isRunning():
            variable.start(startOFW)
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

