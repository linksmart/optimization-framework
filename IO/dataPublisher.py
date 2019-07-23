"""
Created on Jun 27 15:28 2018

@author: nishit
"""

import threading

import time
from abc import ABC, abstractmethod
from random import randrange

from IO.MQTTClient import MQTTClient
from IO.ZMQClient import ZMQClient
from utils_intern.messageLogger import MessageLogger

class DataPublisher(ABC,threading.Thread):

    def __init__(self, internal, topic_params, config, publish_frequency, id=None):
        super().__init__()
        self.logger = MessageLogger.get_logger(__name__, id)
        self.internal = internal
        self.config = config
        self.channel = "MQTT"
        self.id = id
        self.logger.debug("id = " + str(self.id))
        if internal:
            self.channel = config.get("IO", "channel")
        if topic_params is None:
            self.topic_params = {}
        else:
            self.topic_params = topic_params
        self.publish_frequency = publish_frequency

        self.stopRequest = threading.Event()

        if self.channel == "MQTT":
            self.init_mqtt()
        elif self.channel == "ZMQ":
            self.init_zmq()

        self.logger.info("Initializing data publisher thread for topic " + str(self.topic_params))

    def init_mqtt(self):
        self.mqtt = None
        try:
            if "pub.mqtt.host" in dict(self.config.items("IO")):
                self.host = self.config.get("IO", "pub.mqtt.host")
            else:
                self.host = self.config.get("IO", "mqtt.host")
            self.port = self.config.get("IO", "mqtt.port")
            if "mqtt.port" in self.topic_params.keys():
                self.port = self.topic_params["mqtt.port"]
            if "qos" in self.topic_params.keys():
                self.qos = int(self.topic_params["qos"])
            else:
                self.qos = 1
            self.client_id = "client_publish" + str(randrange(100000)) + str(time.time()).replace(".","")
            self.mqtt = MQTTClient(str(self.host), self.port, self.client_id,
                                   username=self.config.get("IO", "mqtt.username", fallback=None),
                                   password=self.config.get("IO", "mqtt.password", fallback=None),
                                   ca_cert_path=self.config.get("IO", "mqtt.ca.cert.path", fallback=None),
                                   set_insecure=bool(self.config.get("IO", "mqtt.insecure.flag", fallback=False)),
                                   id=self.id)
        except Exception as e:
            self.logger.error(e)
            # error for mqtt will be caught at parent
            raise e

    def init_zmq(self):
        self.host = self.config.get("IO", "zmq.host")
        self.port = self.config.get("IO", "zmq.pub.port")
        self.zmq = ZMQClient(self.host, self.port, None)
        self.zmq.init_publisher(self.id)

    def join(self, timeout=None):
        super(DataPublisher, self).join(timeout)

    def Stop(self):
        self.logger.info("start data publisher thread exit")
        self.stopRequest.set()
        if self.channel == "MQTT" and self.mqtt is not None:
            self.mqtt.MQTTExit()
        elif self.channel == "ZMQ":
            self.zmq.stop()
        if self.isAlive():
            self.join(4)
        self.logger.info("data publisher thread exit")

    def run(self):
        """Get data from internet or any other source"""
        if "topic" not in self.topic_params.keys():
            fetch_topic = True
        else:
            fetch_topic = False
        topic = None
        while not self.stopRequest.is_set():
            if fetch_topic:
                data, topic = self.get_data()
            else:
                data = self.get_data()
            if data:
                self.data_publish(data, topic)
            time.sleep(self.publish_frequency)

    def data_publish(self, data, topic=None):
        if self.channel == "MQTT":
            self.mqtt_publish(data, topic)
        elif self.channel == "ZMQ":
            self.zmq_publish(data, topic)

    def mqtt_publish(self, data, topic=None):
        try:
            if topic is None:
                topic = self.topic_params["topic"]
            if self.internal:
                topic = topic + "/" + self.id
            self.logger.debug("Sending results to mqtt on this topic: " + topic)
            self.mqtt.publish(topic, data, True, self.qos)
            self.logger.debug("Results published")
        except Exception as e:
            self.logger.error(e)

    def zmq_publish(self, data, topic=None):
        if topic is None:
            topic = self.topic_params["topic"]
        if self.internal:
            topic = topic + "/" + self.id
        self.logger.debug("Sending results to zmq on this topic: " + topic)
        self.zmq.publish_message(topic, data)
        self.logger.debug("Results published")

    @abstractmethod
    def get_data(self):
        pass
