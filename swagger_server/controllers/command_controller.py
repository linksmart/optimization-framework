import json
import signal
import threading

import connexion
import re
import logging

from pyutilib.pyro import shutdown_pyro_components

from IO.redisDB import RedisDB
from optimization.InvalidModelException import InvalidModelException
from swagger_server.models.start import Start  # noqa: E501

from swagger_server.controllers.threadFactory import ThreadFactory

import os, time
import subprocess


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
        self.lock_key = "id_lock"
        self.name_server_key = "name_server"
        self.dispatch_server_key = "dispatch_server"

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

    def start(self, id, json_object, dict_object=None):
        if json_object is not None:
            self.model_name = json_object.model_name
            self.control_frequency = json_object.control_frequency
            self.horizon_in_steps = json_object.horizon_in_steps
            self.dT_in_seconds = json_object.d_t_in_seconds
            self.repetition = json_object.repetition
            self.solver = json_object.solver
        elif dict_object is not None:
            self.model_name = dict_object["model"]
            self.control_frequency = dict_object["control_frequency"]
            self.horizon_in_steps = dict_object["horizon_in_steps"]
            self.dT_in_seconds = dict_object["dT_in_seconds"]
            self.repetition = dict_object["repetition"]
            self.solver = dict_object["solver"]


        self.start_name_servers()
        self.start_pryo_mip_server()
        self.set(id,
                 ThreadFactory(self.model_name, self.control_frequency, self.horizon_in_steps, self.dT_in_seconds,
                               self.repetition, self.solver, id))

        logger.info("Thread: " + str(self.get(id)))
        self.get(id).startOptControllerThread()
        logger.debug("Thread started")
        self.set_isRunning(id, True)
        logger.debug("Flag isRunning set to True")
        self.statusThread[id] = threading.Thread(target=self.run_status, args=(id,))
        logger.debug("Status of the Thread started")
        self.statusThread[id].start()
        self.redisDB.set("run:"+id, "running")
        self.persist_id(id, True, {"id": id,
                                        "model": self.model_name,
                                        "control_frequency": self.control_frequency,
                                        "horizon_in_steps": self.horizon_in_steps,
                                        "dT_in_seconds": self.dT_in_seconds,
                                        "repetition": self.repetition,
                                        "solver": self.solver,
                                        "ztarttime": time.time()})
        logger.info("running status " + str(self.running))
        logger.debug("Command controller start finished")

    def stop(self, id):
        logger.debug("Stop signal received")
        logger.debug("This is the factory object: " + str(self.get(id)))
        if self.factory[id]:
            self.persist_id(id, False, None)
            self.factory[id].stopOptControllerThread()
            self.stop_pyro_servers()
            self.stop_name_servers()
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

    def persist_id(self, id, start, meta_data):
        path = "/usr/src/app/utils/ids_status.txt"
        try:
            if self.redisDB.get_lock(self.lock_key, id):
                if start:
                    with open(path, "a+") as f:
                        f.write(json.dumps(meta_data,sort_keys=True,separators=(', ', ': '))+"\n")
                else:
                    if os.path.exists(path):
                        data = []
                        with open(path, "r") as f:
                            data = f.readlines()
                        lines = []
                        if len(data) > 0:
                            for s in data:
                                if id in s:
                                    lines.append(s)
                            for line in lines:
                                if line in data:
                                    data.remove(line)
                            with open(path, "w") as f:
                                f.writelines(data)
        except Exception as e:
            logging.error("error persisting id " + id + " " + str(start) + " " + str(e))
        finally:
            self.redisDB.release_lock(self.lock_key, id)

    def get_ids(self):
        path = "/usr/src/app/utils/ids_status.txt"
        if os.path.exists(path):
            old_ids = []
            try:
                if self.redisDB.get_lock(self.lock_key, "start"):
                    data = []
                    with open(path, "r") as f:
                        data = f.readlines()
                    if len(data) > 0:
                        for s in data:
                            a = s.replace("\n", "")
                            if self.redisDB.get_start_time() > float(a[a.find("\"ztarttime\": ") + 13:-1]):
                                old_ids.append(s)
                        for s in old_ids:
                            if s in data:
                                data.remove(s)
                        with open(path, "w") as f:
                            f.writelines(data)
            except Exception as e:
                logging.error("error reading ids file " + str(e))
            finally:
                self.redisDB.release_lock(self.lock_key, "start")
            for s in old_ids:
                val = json.loads(s)
                self.start(val["id"], None, val)

    def number_of_active_ids(self):
        num = 0
        path = "/usr/src/app/utils/ids_status.txt"
        if os.path.exists(path):
            try:
                if self.redisDB.get_lock(self.lock_key, "start"):
                    data = []
                    with open(path, "r") as f:
                        data = f.readlines()
                        num = len(data)
            except Exception as e:
                logging.error("error reading ids file " + str(e))
            finally:
                self.redisDB.release_lock(self.lock_key, "start")
        return num

    def start_name_servers(self):
        logger.debug("Starting name_server and dispatch_server")
        self.subprocess_server_start("/usr/local/bin/pyomo_ns", "name server", self.name_server_key)
        self.subprocess_server_start("/usr/local/bin/dispatch_srvr", "dispatch server", self.dispatch_server_key)

    def subprocess_server_start(self, command, server_name, redis_key=None):
        pid = self.redisDB.get(redis_key)
        if pid is None:
            try:
                logger.debug("Trying to start "+server_name)
                pid = subprocess.Popen([command], preexec_fn=os.setsid, shell=True).pid
                logger.debug(server_name + "  started, pid = " + str(pid))
                if redis_key is not None:
                    self.redisDB.set(redis_key, pid)
            except Exception as e:
                logger.error(server_name+" already exists error")
        return pid

    def stop_name_servers(self):
        if self.number_of_active_ids() == 0:
            pid = self.redisDB.get(self.name_server_key)
            self.os_proc_stop(pid, "name server", self.name_server_key)
            pid = self.redisDB.get(self.dispatch_server_key)
            self.os_proc_stop(pid, "dispatch server", self.dispatch_server_key)

    def os_proc_stop(self, pid, server_name, redis_key=None):
        if pid is not None:
            try:
                os.killpg(os.getpgid(int(pid)), signal.SIGTERM)
                logger.debug(server_name+" stoped : " + str(pid))
                if redis_key is not None:
                    self.redisDB.remove(redis_key)
            except Exception as e:
                logger.error(server_name+" kill error "+str(e))

    def stop_pyro_servers(self):
        logger.info("stop pyro server init")
        logger.debug("active ids = "+str(self.number_of_active_ids()))
        count = 0
        if self.number_of_active_ids() == 0:
            self.redisDB.set("pyro_mip", 0)
            keys = self.redisDB.get_keys_for_pattern("pyro_mip_pid:*")
            if keys is not None:
                for key in keys:
                    pid = int(self.redisDB.get(key))
                    self.os_proc_stop(pid, "mip server "+str(pid), key)
                    count += 1
                active_pyro_servers = int(self.redisDB.get("pyro_mip", 0))
                active_pyro_servers -= count
                if active_pyro_servers < 0:
                    active_pyro_servers = 0
                self.redisDB.set("pyro_mip", active_pyro_servers)
            else:
                logger.info("keys is none")

    def start_pryo_mip_server(self):
        active_pyro_servers = int(self.redisDB.get("pyro_mip",0))
        if active_pyro_servers <= self.number_of_active_ids():
            ###pyro_mip_server
            pyro_mip_server_pid = self.subprocess_server_start("/usr/local/bin/pyro_mip_server", "mip server")
            self.redisDB.set("pyro_mip", active_pyro_servers+1)
            self.redisDB.set("pyro_mip_pid:"+str(pyro_mip_server_pid), pyro_mip_server_pid)

variable = CommandController()
variable.get_ids()

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
        dir = os.path.join(os.getcwd(), "utils", str(id))
        if not os.path.exists(dir):
            return "Id not existing"
        redis_db = RedisDB()
        flag = redis_db.get("run:" + id)
        if flag is not None and flag == "running":
            return "System already running"
        else:
            try:
                variable.start(id, startOFW)
                return "System started succesfully"
            except InvalidModelException as e:
                logger.error("Error " + str(e))
                return str(e)
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
