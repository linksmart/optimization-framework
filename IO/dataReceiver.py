"""
Created on Jun 27 17:36 2018

@author: nishit
"""

import json
import logging

import time
from abc import ABC, abstractmethod

from os.path import commonprefix
from random import randrange
from IO.redisDB import RedisDB

from IO.MQTTClient import MQTTClient
from IO.ZMQClient import ZMQClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class DataReceiver(ABC):

    def __init__(self, internal, topic_params, config, emptyValue={}, id=None, section=None):
        super().__init__()
        self.stop_request = False
        self.internal = internal
        self.topic_params = topic_params
        self.emptyValue = emptyValue
        self.data = self.emptyValue.copy()
        self.data_update = False
        self.config = config
        self.channel = "MQTT"
        self.redisDB = RedisDB()
        self.topics = None
        self.port = None
        self.host_params = {}
        self.id = id
        self.section = section
        if self.section is None:
            self.section = "IO"
        self.setup()

        if self.channel == "MQTT":
            if not self.redisDB.get("Error mqtt"):
                self.init_mqtt(self.topics)
            else:
                logger.error("Error while starting mqtt")
        elif self.channel == "ZMQ":
            self.init_zmq(self.topics)

    def setup(self):
        if self.internal:
            self.channel = self.config.get("IO", "channel")
            self.topics, self.host_params = self.get_internal_channel_params()
        else:
            self.topics, self.host, self.host_params = self.get_external_channel_params()

    def get_external_channel_params(self):
        topic_qos = []
        host_params = {}
        # read from config
        if "sub.mqtt.host" in dict(self.config.items(self.section)):
            host = self.config.get(self.section, "sub.mqtt.host")
        else:
            host = self.config.get("IO", "mqtt.host")
        host_params["username"] = self.config.get("IO", "mqtt.username", fallback=None)
        host_params["password"] = self.config.get("IO", "mqtt.password", fallback=None)
        host_params["ca_cert_path"] = self.config.get("IO", "mqtt.ca.cert.path", fallback=None)
        host_params["insecure_flag"] = bool(self.config.get("IO", "mqtt.insecure.flag", fallback=False))
        if "mqtt.username" in dict(self.config.items(self.section)):
            host_params["username"] = self.config.get(self.section, "mqtt.username", fallback=None)
        if "mqtt.password" in dict(self.config.items(self.section)):
            host_params["password"] = self.config.get(self.section, "mqtt.password", fallback=None)
        if "mqtt.ca.cert.path" in dict(self.config.items(self.section)):
            host_params["ca_cert_path"] = self.config.get(self.section, "mqtt.ca.cert.path", fallback=None)
        if "mqtt.insecure.flag" in dict(self.config.items(self.section)):
            host_params["insecure_flag"] = bool(self.config.get(self.section, "mqtt.insecure.flag", fallback=False))
        qos = 0
        if self.topic_params:
            topic = self.topic_params["topic"]
            if "host" in self.topic_params.keys():
                host = self.topic_params["host"]
            if "qos" in self.topic_params.keys():
                qos = self.topic_params["qos"]
            if "mqtt.port" in self.topic_params.keys():
                self.port = self.topic_params["mqtt.port"]
            if "username" in self.topic_params.keys():
                host_params["username"] = self.topic_params["username"]
            if "password" in self.topic_params.keys():
                host_params["password"] = self.topic_params["password"]
            if "ca_cert_path" in self.topic_params.keys():
                host_params["ca_cert_path"] = self.topic_params["ca_cert_path"]
            if "insecure" in self.topic_params.keys():
                host_params["insecure_flag"] = self.topic_params["insecure"]
            topic_qos.append((topic, qos))
        return topic_qos, host, host_params

    def get_internal_channel_params(self):
        if self.channel == "MQTT":
            topic_qos = []
            host_params = {}
            for k, v in self.topic_params.items():
                if k == "topic":
                    topic_qos.append((v + "/" + self.id,1))
                elif k == "mqtt.port":
                    self.port = v
            self.host = self.config.get("IO", "mqtt.host")
            host_params["username"] = self.config.get("IO", "mqtt.username", fallback=None)
            host_params["password"] = self.config.get("IO", "mqtt.password", fallback=None)
            host_params["ca_cert_path"] = self.config.get("IO", "mqtt.ca.cert.path", fallback=None)
            host_params["insecure_flag"] = bool(self.config.get("IO", "mqtt.insecure.flag", fallback=False))
            return topic_qos, host_params
        elif self.channel == "ZMQ":
            topics = []
            for k, v in self.topic_params.items():
                if k == "topic":
                    topics.append(v + "/" + self.id)
            self.port = self.config.get("IO", "zmq.sub.port")
            self.host = self.config.get("IO", "zmq.host")
            return topics, None

    def init_mqtt(self, topic_qos):
        logger.info("Initializing mqtt subscription client")
        self.redisDB.set("Error mqtt"+self.id, False)
        try:
            if not self.port:
                self.port = 1883
                #read from config
            self.client_id = "client_receive" + str(randrange(100000)) + str(time.time()).replace(".","")
            self.mqtt = MQTTClient(str(self.host), self.port, self.client_id,
                               username=self.host_params["username"], password=self.host_params["password"],
                               ca_cert_path=self.host_params["ca_cert_path"], set_insecure=self.host_params["insecure_flag"])
            self.mqtt.subscribe(topic_qos, self.on_msg_received)
            while not self.mqtt.subscribe_ack_wait():
                self.mqtt.subscribe(topic_qos, self.on_msg_received)
                logger.error("Topic subscribe missing ack")

            logger.info("successfully subscribed")
        except Exception as e:
            self.redisDB.set("Error mqtt"+self.id, True)
            logger.error(e)

    def init_zmq(self, topics):
        logger.info("Initializing zmq subscription client")
        self.zmq = ZMQClient(self.host, None, self.port)
        self.zmq.init_subscriber(topics, self.id)

    @abstractmethod
    def on_msg_received(self, payload):
        pass

    def get_mqtt_data(self, require_updated, clearData):
        if require_updated == 1 and not self.data:
            require_updated = 0
        while require_updated == 0 and not self.data_update and not self.stop_request:
            logger.debug("wait for data")
            time.sleep(0.5)
        return self.get_and_update_data(clearData)

    def exit(self):
        self.stop_request = True
        if self.channel == "MQTT":
            self.mqtt.MQTTExit()
        elif self.channel == "ZMQ":
            self.zmq.stop()
        logger.info("InputController safe exit")

    def get_zmq_msg(self, clearData):
        while True and not self.stop_request:
            logger.debug("get zmq msg")
            flag, topic, message = self.zmq.receive_message()
            logger.debug("zmq subscription msg received for topic "+str(topic)+" for id "+str(self.id))
            if flag:
                self.on_msg_received(message)
                break
            time.sleep(1)
        return self.get_and_update_data(clearData)

    def get_and_update_data(self, clearData):
        new_data = self.data.copy()
        self.data_update = False
        if clearData:
            self.data = self.emptyValue.copy()
        return new_data

    def get_data(self, require_updated=0, clearData=False):
        """

        :param require_updated: 0 -> wait for new data
                                1 -> wait for new data if no prev data
                                2 -> return prev data, even if empty
        :return:
        """
        data = {}
        if self.channel == "MQTT":
            data = self.get_mqtt_data(require_updated, clearData)
        elif self.channel == "ZMQ":
            data = self.get_zmq_msg(clearData)
        return data
