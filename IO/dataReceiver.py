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

from IO.MQTTClient import MQTTClient
from IO.ZMQClient import ZMQClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class DataReceiver(ABC):

    def __init__(self, internal, topic_params, config, emptyValue={}):
        super().__init__()
        self.stop_request = False
        self.internal = internal
        self.topic_params = topic_params
        self.emptyValue = emptyValue
        self.data = self.emptyValue.copy()
        self.data_update = False
        self.config = config
        self.channel = "MQTT"
        self.topics = None
        self.port = None
        self.setup()

        if self.channel == "MQTT":
            self.init_mqtt(self.topics)
        elif self.channel == "ZMQ":
            self.init_zmq(self.topics)

    def setup(self):
        if self.internal:
            self.channel = self.config.get("IO", "channel")
            self.topics = self.get_internal_channel_params()
        else:
            self.topics, self.host = self.get_external_channel_params()

    def get_external_channel_params(self):
        topic_qos = []
        # read from config
        host = self.config.get("IO", "mqtt.host")
        if self.topic_params:
            topic = self.topic_params["topic"]
            host = self.topic_params["host"]
            qos = self.topic_params["qos"]
            topic_qos.append((topic, qos))
        return topic_qos, host

    def get_internal_channel_params(self):
        if self.channel == "MQTT":
            topic_qos = []
            for topic in self.topic_params:
                for k, v in topic.items():
                    if k == "topic":
                        topic_qos.append((v,1))
                    elif k == "mqtt.port":
                        self.port = v
            self.host = self.config.get("IO", "mqtt.host")
            return topic_qos
        elif self.channel == "ZMQ":
            port_list = []
            topics = []
            for topic in self.topic_params:
                for k, v in topic.items():
                    if k == "topic":
                        topics.append(v)
                    elif k == "zmq.port":
                        port_list.append(v)
            self.port = port_list
            self.host = self.config.get("IO", "zmq.host")
            return commonprefix(topics)

    def init_mqtt(self, topic_qos):
        logger.info("Initializing mqtt subscription client")
        if not self.port:
            self.port = 1883
            #read from config
        self.client_id = "client_receive" + str(randrange(100000)) + str(time.time()).replace(".","")
        self.mqtt = MQTTClient(str(self.host), self.port, self.client_id)
        self.mqtt.subscribe(topic_qos, self.on_msg_received)
        if not self.mqtt.subscribe_ack_wait():
            logger.error("Topic subscribe missing ack")
        logger.info("successfully subscribed")

    def init_zmq(self, topics):
        logger.info("Initializing zmq subscription client")
        self.zmq = ZMQClient(self.host, self.port)
        self.zmq.init_subscriber(topics)

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
        logger.info("InputController safe exit")

    def get_zmq_msg(self, clearData):
        while True and not self.stop_request:
            logger.debug("get zmq msg")
            flag, topic, message = self.zmq.receive_message()
            logger.debug("zmq subscription msg received")
            logger.info(message)
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
