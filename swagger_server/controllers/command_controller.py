import threading

import connexion
import re
import logging

from IO.redisDB import RedisDB
from swagger_server.models.start import Start  # noqa: E501

from swagger_server.controllers.threadFactory import ThreadFactory

import os, time

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class CommandController:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if CommandController._instance is None:
            with CommandController._lock:
                if CommandController._instance is None:
                    CommandController._instance = super(CommandController, cls).__new__(cls)
        return CommandController._instance

    def __init__(self):
        self.factory = {}
        self.statusThread = {}
        self.running = {}
        self.redisDB = RedisDB()

    def set(self, id, object):
        self.factory[id] = object

    def get(self, id):
        return self.factory[id]

    def set_isRunning(self, id, bool):
        self.running[id] = bool

    def isRunningExists(self):
        logger.debug("IsRunning exists: " + str(len(self.running)))
        if len(self.running):
            return True
        else:
            return False

    def get_isRunning(self, id):
        if id in self.running.keys():
            return self.running[id]
        else:
            return False

    def get_running(self):
        return self.running

    def get_statusThread(self, id):
        return self.statusThread[id]

    def start(self, id, json_object):
        self.model_name = json_object.model_name
        self.time_step = json_object.time_step
        self.horizon = json_object.horizon
        self.repetition = json_object.repetition
        self.solver = json_object.solver
        self.id = id

        self.set(self.id,
                 ThreadFactory(self.model_name, self.time_step, self.horizon, self.repetition, self.solver, self.id))

        logger.info("Thread: " + str(self.get(self.id)))
        self.get(self.id).startOptControllerThread()
        logger.debug("Thread started")
        self.set_isRunning(self.id, True)
        logger.debug("Flag isRunning set to True")
        self.statusThread[self.id] = threading.Thread(target=self.run_status, args=(self.id,))
        logger.debug("Status of the Thread started")
        self.statusThread[self.id].start()
        logger.debug("Command controller start finished")
        logger.info("running status " + str(self.running))
        self.redisDB.set("run:"+self.id, "running")

    def stop(self, id):
        logger.debug("Stop signal received")
        logger.debug("This is the factory object: " + str(self.get(id)))
        if self.factory[id]:
            self.factory[id].stopOptControllerThread()
            self.set_isRunning(id, False)
            message = "System stopped succesfully"
            logger.debug(message)
        else:
            message = "No threads found"
            logger.debug(message)

    def run_status(self, id):
        while True:
            status = self.get(id).is_running()
            flag = self.redisDB.get("run:" + id)
            if not status or (flag is not None and flag == "stop"):
                self.redisDB.remove("run:" + id)
                self.stop(id)
                break
            time.sleep(1)

variable = CommandController()

def get_models():
    f = []
    mypath = "/usr/src/app/optimization/models"
    for (dirpath, dirnames, filenames) in os.walk(mypath):
        f.extend(filenames)
        break
    f_new = []
    for filenames in f:
        filenames = re.sub('.py', '', str(filenames))
        f_new.append(filenames)
    logger.debug("available models = " + str(f_new))
    return f_new


def framework_start(id, startOFW):  # noqa: E501
    """Command for starting the framework

    # noqa: E501

    :param startOFW: Start command for the optimization framework
    :type startOFW: dict | bytes

    :rtype: None
    """
    available_solvers = ["ipopt", "glpk", "bonmin"]
    if connexion.request.is_json:
        logger.info("Starting the system")
        startOFW = Start.from_dict(connexion.request.get_json())
        models = get_models()
        if startOFW.model_name != "" and startOFW.model_name not in models:
            return "Model not available. Available models are :" + str(models)
        if startOFW.solver not in available_solvers:
            return "Use one of the following solvers :" + str(available_solvers)
        if variable.isRunningExists():
            logger.debug("isRunning exists")
            if not variable.get_isRunning(id):
                variable.start(id, startOFW)
                return "System started succesfully"
            else:
                logger.debug("System already running")
                return "System already running"
        else:
            logger.debug("isRunning not created yet")
            variable.start(id, startOFW)
            return "System started succesfully"

    else:
        logger.error("Wrong Content-Type")
        return "Wrong Content-Type"
    # return 'System started succesfully'


def framework_stop(id):  # noqa: E501
    """Command for stoping the framework

    # noqa: E501


    :rtype: None
    """
    try:
        redis_db = RedisDB()
        flag = redis_db.get("run:" + id)
        message = ""
        if flag is not None and flag == "running":
            logger.debug("System running and trying to stop")
            redis_db.set("run:" + id, "stop")
            time.sleep(1)
            flag = redis_db.get("run:" + id)
            if flag is None:
                logger.debug("System stopped succesfully")
                message = "System stopped succesfully"
        elif flag is None:
            logger.debug("System already stopped")
            message = "System already stopped"
    except Exception as e:
        logger.error(e)
        message = "Error stoping the system"
    return message
