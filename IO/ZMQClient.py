"""
Created on Jun 11 12:57 2018

@author: nishit
"""
import threading

import zmq
import time

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class ZMQClient:

    def __init__(self, host, pubPort, subPort):
        self.host = host
        self.pubPort = pubPort
        self.subPort = subPort
        self.context = zmq.Context()
        self.pubUrl = 'tcp://{}:{}'.format(self.host, self.pubPort)
        self.subUrl = 'tcp://{}:{}'.format(self.host, self.subPort)
        logger.info("Initialize ZMQClient")

    def init_publisher(self, id=None):
        try:
            logger.info("Initialize zmq publisher with url " + str(self.pubUrl) + " for id " + str(id))
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.connect(self.pubUrl)
            time.sleep(1)
            logger.info("publisher initialized")
        except Exception as e:
            logger.error(e)

    def stop(self):
        pass

    def init_subscriber(self, topics, id=None):
        try:
            logger.info("Initialize zmq subscriber with url " + str(self.subUrl) + " for id " + str(id))
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect(self.subUrl)
            for topic in topics:
                logger.debug("filter = " + str(topic))
                self.subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)
            logger.info("subscriber initialized")
        except Exception as e:
            logger.error(e)

    def publish_message(self, topic, message):
        try:
            self.publisher.send_string("%s %s" % (topic, message))
            logger.info("publish")
        except Exception as e:
            logger.error(e)

    def receive_message(self):
        try:
            logger.debug("try receiving msg")
            messagedata = self.subscriber.recv_string()
            topic, message = messagedata.split(" ", 1)
            logger.debug(topic + " " + message)
            return True, topic, message
        except zmq.Again as e:
            logger.debug("No messages received yet. Error = " + str(e))
            return False, None, None
        except Exception as e:
            logger.error(e)
            return False, None, None


class ForwarderDevice(threading.Thread):

    def __init__(self, host, pubPort, subPort):
        super().__init__()
        self.host = host
        self.pubPort = pubPort
        self.subPort = subPort
        self.frontend = None
        self.backend = None
        self.context = None

    def run(self):
        logger.info("init zmq forwarder")
        try:
            self.context = zmq.Context(2)
            # Socket facing clients
            url = 'tcp://{}:{}'.format(self.host, self.pubPort)
            self.frontend = self.context.socket(zmq.SUB)
            self.frontend.bind(url)

            self.frontend.setsockopt_string(zmq.SUBSCRIBE, "")

            # Socket facing services
            url = 'tcp://{}:{}'.format(self.host, self.subPort)
            self.backend = self.context.socket(zmq.PUB)
            self.backend.bind(url)

            logger.info("create forwarder device")
            zmq.device(zmq.FORWARDER, self.frontend, self.backend)
            logger.info("created forwarder device")
        except Exception as e:
            logger.error(e)
            logger.info("bringing down zmq device")
        finally:
            logger.info("finally forwarder device")
            if self.frontend:
                self.frontend.close()
            if self.backend:
                self.backend.close()
            if self.context:
                self.context.term()

    def Stop(self):
        logger.info("closing forwarder device")
        if self.frontend:
            self.frontend.close()
        if self.backend:
            self.backend.close()
        if self.context:
            self.context.term()
