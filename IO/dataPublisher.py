"""
Created on Jun 27 15:28 2018

@author: nishit
"""

import logging
import threading

import time
from abc import ABC, abstractmethod
from random import randrange

from IO.MQTTClient import MQTTClient
from IO.ZMQClient import ZMQClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class DataPublisher(ABC,threading.Thread):

    def __init__(self, internal, topic_params, config, publish_frequency):
        super().__init__()
        self.internal = internal
        self.config = config
        self.channel = "MQTT"
        if internal:
            self.channel = config.get("IO", "channel")
        self.topic_params = topic_params
        self.stopRequest = threading.Event()
        if self.channel == "MQTT":
            self.init_mqtt()
        elif self.channel == "ZMQ":
            self.init_zmq()
        self.publish_frequency = publish_frequency

        logger.info("Initializing data publisher thread for topic " + str(self.topic_params["topic"]))

    def init_mqtt(self):
        self.host = self.config.get("IO", "mqtt.host")
        self.port = self.topic_params["mqtt.port"]
        self.qos = 1
        self.client_id = "client_publish" + str(randrange(100))
        self.mqtt = MQTTClient(str(self.host), self.port, self.client_id)

    def init_zmq(self):
        self.host = self.config.get("IO", "zmq.host")
        self.port = self.topic_params["zmq.port"]
        self.zmq = ZMQClient(self.host, self.port)
        self.zmq.init_publisher()

    def join(self, timeout=None):
        super(DataPublisher, self).join(timeout)

    def Stop(self):
        logger.info("start data publisher thread exit")
        self.stopRequest.set()
        if self.channel == "MQTT":
            self.mqtt.MQTTExit()
        elif self.channel == "ZMQ":
            self.zmq.stop()
        if self.isAlive():
            self.join()
        logger.info("data publisher thread exit")

    def run(self):
        """Get data from internet or any other source"""
        while not self.stopRequest.is_set():
            data = self.get_data()
            if data:
                self.data_publish(data)
            time.sleep(self.publish_frequency)

    def data_publish(self, data):
        if self.channel == "MQTT":
            self.mqtt_publish(data)
        elif self.channel == "ZMQ":
            self.zmq_publish(data)

    def mqtt_publish(self, data):
        try:
            logger.info("Sending results to mqtt on this topic: " + self.topic_params["topic"])
            logger.debug("MQTT Data: "+str(data))
            self.mqtt.publish(self.topic_params["topic"], data, True)
            logger.debug("Results published")
        except Exception as e:
            logger.error(e)

    def zmq_publish(self, data):
        logger.info("Sending results to zmq on this topic: " + self.topic_params["topic"])
        self.zmq.publish_message(self.topic_params["topic"], data)
        logger.debug("Results published")

    @abstractmethod
    def get_data(self):
        pass
