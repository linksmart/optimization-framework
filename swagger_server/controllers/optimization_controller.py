import json
import signal
import threading

import connexion
import re

import os
import subprocess
import time
import gc

import psutil

from IO.MQTTClient import InvalidMQTTHostException

from IO.redisDB import RedisDB
from optimization.ModelException import InvalidModelException, MissingKeysException
from swagger_server.controllers.threadFactory import ThreadFactory
from swagger_server.models.start import Start  # noqa: E501
from swagger_server.models.status_output import StatusOutput  # noqa: E501
from optimization.idStatusManager import IDStatusManager
from utils_intern.constants import Constants

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


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
        self.lock_key = "id_lock"

    def set(self, id, object):
        self.factory[id] = object

    def get_length_factory(self):
        return len(self.factory)

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

    def start(self, id, json_object, dict_object=None):
        logger.debug(str(json_object))
        if json_object is not None:
            self.model_name = json_object.model_name
            self.control_frequency = json_object.control_frequency
            self.horizon_in_steps = json_object.horizon_in_steps
            self.dT_in_seconds = json_object.d_t_in_seconds
            self.repetition = json_object.repetition
            self.solver = json_object.solver
            self.optimization_type = json_object.optimization_type
            self.single_ev = json_object.single_ev
        elif dict_object is not None:
            self.model_name = dict_object["model"]
            self.control_frequency = dict_object["control_frequency"]
            self.horizon_in_steps = dict_object["horizon_in_steps"]
            self.dT_in_seconds = dict_object["dT_in_seconds"]
            self.repetition = dict_object["repetition"]
            self.solver = dict_object["solver"]
            self.optimization_type = dict_object["optimization_type"]
            self.single_ev = dict_object["single_ev"]

        self.set(id,
                 ThreadFactory(self.model_name, self.control_frequency, self.horizon_in_steps, self.dT_in_seconds,
                               self.repetition, self.solver, id, self.optimization_type, self.single_ev))

        logger.info("Thread: " + str(self.get(id)))
        self.redisDB.set("run:" + id, "starting")
        msg = self.get(id).startOptControllerThread()
        logger.debug("Answer from Thread factory" + str(msg))
        if msg == 0:
            self.set_isRunning(id, True)
            logger.debug("Flag isRunning set to True")
            self.statusThread[id] = threading.Thread(target=self.run_status, args=(id,))
            logger.debug("Status of the Thread started")
            self.statusThread[id].start()
            meta_data = {"id": id,
                         "model": self.model_name,
                         "control_frequency": self.control_frequency,
                         "horizon_in_steps": self.horizon_in_steps,
                         "dT_in_seconds": self.dT_in_seconds,
                         "repetition": self.repetition,
                         "solver": self.solver,
                         "optimization_type": self.optimization_type,
                         "single_ev": self.single_ev,
                         "ztarttime": time.time()}
            self.redisDB.set("run:" + id, "running")
            IDStatusManager.persist_id(id, True, meta_data, self.redisDB)
            logger.info("running status " + str(self.running))
            logger.debug("Command controller start finished")
            return 0
        else:
            self.set_isRunning(id, False)
            logger.debug("Flag isRunning set to False")
            IDStatusManager.persist_id(id, False, None, self.redisDB)
            self.factory[id].stopOptControllerThread()
            self.redisDB.set("run:" + id, "stopped")
            logger.error("Command controller start could not be finished")
            # logger.debug("System stopped succesfully")
            return 1

    def stop(self, id):

        logger.debug("Stop signal received")
        logger.debug("This is the factory object: " + str(self.get(id)))
        if self.factory[id]:
            IDStatusManager.persist_id(id, False, None, self.redisDB)
            self.factory[id].stopOptControllerThread()
            del self.factory[id]
            del self.statusThread[id]
            #self.stop_pyro_servers()
            #self.stop_name_servers()
            self.set_isRunning(id, False)
            message = "System stopped succesfully"
            self.redisDB.set("run:" + id, "stopped")
            logger.debug(message)
            gc.collect()
        else:
            message = "No threads found"
            logger.debug(message)

    def run_status(self, id):
        while True:
            status = self.get(id).is_running()
            flag = self.redisDB.get("run:" + id)
            if not status or (flag is not None and flag == "stop"):
                self.redisDB.set("run:" + id, "stopping")
                self.stop(id)
                break
            time.sleep(1)

    def restart_ids(self):
        old_ids, stopped_ids = IDStatusManager.instances_to_restart(self.redisDB)
        for s in old_ids:
            val = json.loads(s)
            try:
                self.start(val["id"], None, val)
            except (InvalidModelException, MissingKeysException, InvalidMQTTHostException) as e:
                # TODO: should we catch these exceptions here?
                logger.error("Error " + str(e))
                self.redisDB.set("run:" + val["id"], "stopped")
                return str(e)
        for s in stopped_ids:
            val = json.loads(s)
            id = val["id"]
            self.redisDB.set("run:" + id, "stopped")
            self.redisDB.set(Constants.id_meta + ":" + id, json.dumps(val))

    def get_status(self):
        status = {}
        keys = self.redisDB.get_keys_for_pattern("run:*")
        if keys is not None:
            for key in keys:
                value = self.redisDB.get(key)
                id = key[4:]
                status[id] = {}
                if value is None or (value is not None and value == "stopped"):
                    status[id]["status"] = "stopped"
                elif value == "running":
                    status[id]["status"] = "running"
                elif value == "stop" or value == "stopping":
                    status[id]["status"] = "stopping"
                elif value == "starting":
                    status[id]["status"] = "starting"
        keys = self.redisDB.get_keys_for_pattern(Constants.id_meta + ":*")
        if keys is not None:
            for key in keys:
                value = self.redisDB.get(key)
                id = key[8:]
                if id not in status.keys():
                    status[id] = {}
                    status[id]["status"] = "stopped"
                status[id]["config"] = {}
                if value is not None:
                    status[id]["config"].update(json.loads(value))
                    # logger.debug("status id config "+str(status))
                    if "ztarttime" in status[id]["config"].keys():
                        status[id]["start_time"] = status[id]["config"]["ztarttime"]
                        status[id]["config"].pop("ztarttime")
                    if "model" in status[id]["config"].keys():
                        status[id]["config"]["model_name"] = status[id]["config"]["model"]
                        status[id]["config"].pop("model")
        return status


variable = CommandController()
variable.restart_ids()


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

    :param id: Id of the registry to be started
    :type id: str
    :param startOFW: Start command for the optimization framework   repetitions: -1 infinite repetitions
    :type startOFW: dict | bytes

    :rtype: None
    """

    available_solvers = ["ipopt", "glpk", "bonmin", "gurobi", "cbc"]
    available_optimizers = ["discrete", "stochastic", "MPC"]
    response_msg = ""
    response_code = 200
    if connexion.request.is_json:
        logger.info("Starting the system")
        startOFW = Start.from_dict(connexion.request.get_json())
        models = get_models()
        if startOFW.model_name != "" and startOFW.model_name not in models:
            response_msg = "Model not available. Available models are :" + str(models)
            response_code = 400
        elif startOFW.solver not in available_solvers:
            response_msg = "Use one of the following solvers :" + str(available_solvers)
            response_code = 400
        elif startOFW.optimization_type not in available_optimizers:
            response_msg = "Use one of the following optimizer types : " + str(available_optimizers)
            response_code = 400
        else:
            dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
            if not os.path.exists(dir):
                response_msg = "Id not existing"
                response_code = 400
            else:
                redis_db = RedisDB()
                flag = redis_db.get("run:" + id)
                if flag is not None and flag == "running":
                    response_msg = "System already running"
                else:
                    try:
                        msg = variable.start(id, startOFW)
                        if msg == 0:
                            response_msg = "System started succesfully"
                        else:
                            response_msg = "System could not start"
                            response_code = 400
                    except (InvalidModelException, MissingKeysException, InvalidMQTTHostException) as e:
                        logger.error("Error " + str(e))
                        redis_db.set("run:" + id, "stopped")
                        response_msg = str(e)
                        response_code = 400
    else:
        response_msg = "Wrong Content-Type"
        response_code = 400
        logger.error("Wrong Content-Type")
    return response_msg, response_code
    # return 'System started succesfully'


def framework_status():  # noqa: E501
    """Command for getting status of the framework

     # noqa: E501


    :rtype: StatusOutput
    """
    results = variable.get_status()
    answer_dict = {}
    if len(results) > 0:
        answer_dict["status"] = results
    response = StatusOutput.from_dict(answer_dict)
    del results
    del answer_dict
    # logger.debug("response: " + str(response2))
    return response


def framework_stop(id):  # noqa: E501
    """Command for stoping the framework

     # noqa: E501

    :param id: Id of the registry to be stopped
    :type id: str

    :rtype: None
    """
    try:
        redis_db = RedisDB()
        flag = redis_db.get("run:" + id)
        logger.debug("Flag " + str(flag))
        message = ""
        code = 200
        if flag is not None and flag == "running":
            logger.debug("System running and trying to stop")
            redis_db.set("run:" + id, "stop")
            time.sleep(1)
            flag = redis_db.get("run:" + id)
            logger.debug("Flag in stop: " + str(flag))

            if flag is "stopped" or None: # TODO: is none necessary?
                logger.debug("System stopped succesfully")
                message = "System stopped succesfully"
            elif "stopping" in flag:
                message = "System stopped succesfully"
                counter = 0
                while ("stopping" in flag):
                    flag = redis_db.get("run:" + id)
                    counter = counter + 1
                    if counter >= 15:
                        message = "system stopped succesfully"
                        break
                    else:
                        time.sleep(1)
                logger.debug("System stopped succesfully")
            else:
                message = "Problems while stopping the system"
                code = 500
        elif flag is not None and flag == "stopped":
            logger.debug("System already stopped")
            message = "System already stopped"
        elif flag is None:
            logger.debug("System already stopped")
            message = "System already stopped"
    except Exception as e:
        logger.error(e)
        message = "Error stoping the system"
        code = 500
    return message, code
