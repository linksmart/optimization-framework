"""
Created on Jun 07 16:09 2018

@author: nishit
"""

import json
import logging

import time
from numbers import Number

from IO.MQTTClient import MQTTClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class InputController:
    """MQTT subcribers to parse data"""
    def __init__(self, topics_qos, host, port):
        super().__init__()
        self.client_id = "client_input"
        self.data = {"update": False}
        self.topics_qos = topics_qos
        # not generalized, need to re-look
        self.callback_functions = {"forecast/load": self.on_msg_received,
                                   "forecast/pv": self.on_msg_received}
        logger.info("Initializing optimization controller")
        self.mqtt = MQTTClient(str(host), port, self.client_id)
        self.mqtt.subscribe(self.topics_qos, self.callback_functions)
        if not self.mqtt.subscribe_ack_wait():
            logger.error("Topic subscribe missing ack")
        logger.info("successfully subscribed")

    def on_msg_received(self, payload):
        logger.debug("Load data received : " + payload)
        data = json.loads(payload)
        self.data.update(self.add_formated_data(data))
        self.data["update"] = True
        logger.info(self.data)

    def data_updated(self):
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
            elif isinstance(v, Number):
                new_data[k] = {None: v}
        return new_data

    def exit(self):
        self.mqtt.MQTTExit()