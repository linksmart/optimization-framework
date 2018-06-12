"""
Created on Jun 07 16:09 2018

@author: nishit
"""

import json
import logging

import time

from os.path import commonprefix

from IO.MQTTClient import MQTTClient
from IO.ZMQClient import ZMQClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class InputController:
    def __init__(self, topic_params, config):
        super().__init__()
        self.topic_params = topic_params
        self.data = {"update": False}
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
            callbackfunctions = {}
            for topic in self.topic_params:
                for k, v in topic.items():
                    if k == "topic":
                        topic_qos.append((v,1))
                        callbackfunctions[v] = self.on_msg_received
                    elif k == "mqtt.port":
                        self.port = v
            self.host = self.config.get("IO", "mqtt.host")
            self.callback_functions = callbackfunctions
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
        self.client_id = "client_input"
        self.mqtt = MQTTClient(str(self.host), self.port, self.client_id)
        self.mqtt.subscribe(topic_qos, self.callback_functions)
        if not self.mqtt.subscribe_ack_wait():
            logger.error("Topic subscribe missing ack")
        logger.info("successfully subscribed")

    def init_zmq(self, topics):
        logger.info("Initializing zmq subscription client")
        self.callback_function = self.on_msg_received
        self.zmq = ZMQClient(self.host, self.port)
        self.zmq.init_subscriber(topics)

    def on_msg_received(self, payload):
        logger.debug("Load data received : " + payload)
        data = json.loads(payload)
        self.data.update(self.add_formated_data(data))
        self.data["update"] = True
        logger.info(self.data)

    def get_mqtt_data(self):
        while not self.data["update"]:
            logger.info("wait for data")
            time.sleep(0.5)
        new_data = self.data.copy()
        new_data.pop("update", None)
        self.data["update"] = False
        return new_data

    def add_formated_data(self, data={}):
        new_data = {}
        for k, v in data.items():
            if isinstance(v, dict):
                new_data[k] = v
            else:
                new_data[k] = {None: v}
        return new_data

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
                data = json.loads(message)
                self.data.update(self.add_formated_data(data))
                break
            time.sleep(1)
        new_data = self.data.copy()
        if new_data.pop("update", None):
            self.data["update"] = False
        return new_data

    def get_data(self):
        data = {}
        if self.channel == "MQTT":
            data = self.get_mqtt_data()
        elif self.channel == "ZMQ":
            data = self.get_zmq_msg()
        return data
