"""
 Created by Gustavo Aragón on 14.03.2018

"""
import configparser
import  os, logging
import subprocess # just to call an arbitrary command e.g. 'ls'
import time
import signal, sys

import swagger_server.__main__ as webserver
#import swagger_server.wsgi as webserver

from optparse import OptionParser

import sh as sh

from IO.ZMQClient import ForwarderDevice
from optimization.controller import OptController


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

"""
Get the address of the data.dat
"""




def startOfw(options):
    # code to start a daemon
    init=0

def parseArgs():
    mandatoryArgs=0


def main():
    global OPTIONS

    logger.info("Optiframework started")
    setup()
    logger.info("Starting webserver")
    webserver.main()


    #while True:

       #results=opt.start()
       #print(results)
       #time.sleep(5)

zmqForwarder = None

def signal_handler(sig, frame):
    logger.info('You pressed Ctrl+C!')
    if zmqForwarder:
        logger.info("stopping zmq forwarder")
        zmqForwarder.Stop()
    sys.exit(0)

def setup():
    clear_redis()
    signal.signal(signal.SIGINT, signal_handler)
    # Creating an object of the configuration file (standard values)
    try:
        config = configparser.RawConfigParser()
        data_file = os.path.join("/usr/src/app", "utils", "ConfigFile.properties")
        config.read(data_file)
    except Exception as e:
        logger.error(e)

    zmqHost = config.get("IO", "zmq.host")
    pubPort = config.get("IO", "zmq.pub.port")
    subPort = config.get("IO", "zmq.sub.port")
    zmqForwarder = ForwarderDevice(zmqHost, pubPort, subPort)
    zmqForwarder.start()


def clear_redis():
    logger.info("reset redis")
    from IO.redisDB import RedisDB
    redisDB = RedisDB()
    redisDB.reset()

if __name__ == "__main__":
        # execute only if run as a script
        main()