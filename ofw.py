import subprocess

"""
 Created by Gustavo Aragón on 14.03.2018

"""
import configparser
import os
import logging
import signal
import sys
import shutil

# import swagger_server.__main__ as webserver
import time

import swagger_server.wsgi as webserver

from IO.ZMQClient import ForwarderDevice
from config.configUpdater import ConfigUpdater

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

"""
Get the address of the data.dat
"""


def startOfw(options):
    # code to start a daemon
    init = 0


def parseArgs():
    mandatoryArgs = 0


def main():
    global OPTIONS

    logger.debug("###################################")
    logger.info("OFW started")
    logger.debug("###################################")

    setup()
    logger.info("Starting webserver")
    webserver.main()

    # while True:

    # results=opt.start()
    # print(results)
    # time.sleep(5)


zmqForwarder = None


def signal_handler(sig, frame):
    logger.info('You pressed Ctrl+C!')
    if zmqForwarder:
        logger.info("stopping zmq forwarder")
        zmqForwarder.Stop()
    sys.exit(0)


def setup():
    config_path = "/usr/src/app/utils/ConfigFile.properties"
    config_path_default = "/usr/src/app/config/ConfigFile.properties"
    ConfigUpdater.copy_config(config_path_default, config_path)

    clear_redis()
    copy_models()
    signal.signal(signal.SIGINT, signal_handler)
    # Creating an object of the configuration file (standard values)
    try:
        config = configparser.RawConfigParser()
        config.read(config_path)
    except Exception as e:
        logger.error(e)

    zmqHost = config.get("IO", "zmq.host")
    pubPort = config.get("IO", "zmq.pub.port")
    subPort = config.get("IO", "zmq.sub.port")
    zmqForwarder = ForwarderDevice(zmqHost, pubPort, subPort)
    zmqForwarder.start()


def copy_models():
    models_path = "/usr/src/app/optimization/resources/models"
    if os.path.exists(models_path):
        for file in os.listdir(models_path):
            file_path = os.path.join(models_path, file)
            if os.path.isfile(file_path) and ".py" in file:
                shutil.copyfile(file_path, os.path.join("/usr/src/app/optimization/models", file))


def clear_redis():
    logger.info("reset redis")
    from IO.redisDB import RedisDB
    redisDB = RedisDB()
    redisDB.reset()
    redisDB.set("time", time.time())


if __name__ == "__main__":
    # execute only if run as a script
    main()
