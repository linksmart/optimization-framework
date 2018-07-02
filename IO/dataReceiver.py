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

    def __init__(self, topic_params, config):
        super().__init__()
        self.topic_params = topic_params
        self.data = {}
        self.data_update = False
        self.config = config
        self.channel = config.get("IO", "channel")
        topics = self.get_channel_params()
        if self.channel == "MQTT":
            self.init_mqtt(topics)
        elif self.channel == "ZMQ":
            self.init_zmq(topics)

    def get_channel_params(self):
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
        self.client_id = "client_receive" + str(randrange(100))
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

    def get_mqtt_data(self, require_updated):
        if require_updated == 1 and not self.data:
            require_updated = 0
        while require_updated == 0 and not self.data_update:
            logger.debug("wait for data")
            time.sleep(0.5)
        return self.get_and_update_data()

    def exit(self):
        if self.channel == "MQTT":
            self.mqtt.MQTTExit()
        logger.info("InputController safe exit")

    def get_zmq_msg(self):
        while True:
            logger.debug("get zmq msg")
            flag, topic, message = self.zmq.receive_message()
            logger.debug("zmq subscription msg received")
            logger.info(message)
            if flag:
                self.on_msg_received(message)
                break
            time.sleep(1)
        return self.get_and_update_data()

    def get_and_update_data(self):
        new_data = self.data.copy()
        self.data_update = False
        return new_data

    def get_data(self, require_updated=0):
        """

        :param require_updated: 0 -> wait for new data
                                1 -> wait for new data if no prev data
                                2 -> return prev data, even if empty
        :return:
        """
        data = {}
        if self.channel == "MQTT":
            data = self.get_mqtt_data(require_updated)
        elif self.channel == "ZMQ":
            data = self.get_zmq_msg()
        return data
