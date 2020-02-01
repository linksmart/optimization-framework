import getpass
import subprocess
import threading
import multiprocessing

from optimization.pyroServerManagement import PyroServerManagement
from utils_intern.messageLogger import MessageLogger
from swagger_server.wsgi import StandaloneApplication

"""
 Created by Gustavo Aragón on 14.03.2018

"""
import configparser
import os
import signal
import sys
import shutil

# import swagger_server.__main__ as webserver
import time

import swagger_server.wsgi as webserver


from IO.ZMQClient import ForwarderDevice
from config.configUpdater import ConfigUpdater

"""
Get the address of the data.dat
"""

class GracefulKiller:
  kill_now = False
  signals = {
    signal.SIGINT: 'SIGINT',
    signal.SIGTERM: 'SIGTERM'
  }

  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self, signum, frame):
    print("\nReceived {} signal".format(self.signals[signum]))
    print("Cleaning up resources. End of the program")
    from IO.redisDB import RedisDB
    redisDB = RedisDB()
    redisDB.set("End ofw", "True")
    time.sleep(6)
    self.kill_now = True


"""def sigterm(x, y):
    print('SIGTERM received, time to leave for OFW')
    from IO.redisDB import RedisDB
    redisDB = RedisDB()
    redisDB.set("End ofw", "True")

# Register the signal to the handler
signal.signal(signal.SIGTERM, sigterm)  # Used by this script"""

def startOfw(options):
    # code to start a daemon
    init = 0


def parseArgs():
    mandatoryArgs = 0


def main():
    global OPTIONS

    logger, redisDB = setup()

    logger.debug("###################################")
    logger.info("OFW started")
    logger.debug("###################################")
    logger.debug("Starting name server and dispatch server")
    #threading.Thread(target=StandaloneApplication.main).start()
    p = multiprocessing.Process(target=StandaloneApplication.main)
    p.start()
    #threading.Thread(target=PyroServerManagement.start_name_servers, args=(redisDB,)).start()
    #threading.Thread(target=PyroServerManagement.start_pryo_mip_servers, args=(redisDB, 5,)).start()
    logger.info("Starting webserver")
    killer = GracefulKiller()
    #webserver.main()
    while not killer.kill_now:
        time.sleep(1)
    p.join(2)


    # while True:

    # results=opt.start()
    # print(results)
    # time.sleep(5)

"""def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    print(sig)
    if zmqForwarder:
        print("stopping zmq forwarder")
        zmqForwarder.Stop()
    sys.exit(0)"""

zmqForwarder = None



def setup():

    config_path = "/usr/src/app/optimization/resources/ConfigFile.properties"
    config_path_default = "/usr/src/app/config/ConfigFile.properties"
    ConfigUpdater.copy_config(config_path_default, config_path)

    # Creating an object of the configuration file (standard values)
    config = configparser.RawConfigParser()
    config.read(config_path)
    log_level = config.get("IO", "log.level", fallback="DEBUG")
    logger = MessageLogger.set_and_get_logger_parent(id="", level=log_level)

    redisDB = clear_redis(logger)
    copy_models()
    copy_pv_files()
    copy_env_varibles()
    #logger.debug("env = "+str(os.environ))
    zmqHost = config.get("IO", "zmq.host")
    pubPort = config.get("IO", "zmq.pub.port")
    subPort = config.get("IO", "zmq.sub.port")
    zmqForwarder = ForwarderDevice(zmqHost, pubPort, subPort)
    zmqForwarder.start()
    return logger, redisDB

def copy_pv_files():
    pv_path = "/usr/src/app/optimization/pv_data"
    if os.path.exists(pv_path):
        for file in os.listdir(pv_path):
            file_path = os.path.join(pv_path, file)
            if os.path.isfile(file_path) and ".txt" in file:
                shutil.copyfile(file_path, os.path.join("/usr/src/app/optimization/resources", file))

def copy_models():
    models_path = "/usr/src/app/optimization/resources/models"
    if os.path.exists(models_path):
        for file in os.listdir(models_path):
            file_path = os.path.join(models_path, file)
            if os.path.isfile(file_path) and ".py" in file:
                shutil.copyfile(file_path, os.path.join("/usr/src/app/optimization/models", file))


def clear_redis(logger):
    logger.info("reset redis")
    from IO.redisDB import RedisDB
    redisDB = RedisDB()
    redisDB.reset()
    redisDB.set("time", time.time())
    redisDB.set("End ofw", "False")
    return redisDB

def copy_env_varibles():
    with open("/usr/src/app/utils_intern/env_var.txt", "r") as f:
        rows = f.readlines()
        for row in rows:
            if len(row) > 0:
                row = row.replace("\n","")
                s = row.split("=")
                if len(s) == 1:
                    s.append("")
                os.environ[s[0]] = str(s[1])

if __name__ == "__main__":
    # execute only if run as a script
    main()
