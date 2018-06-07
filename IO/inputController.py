"""
Created on Jun 07 16:09 2018

@author: nishit
"""

import json
import logging

import time

from IO.MQTTClient import MQTTClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class InputController:
    """MQTT subcribers to parse data"""
    def __init__(self, topics_qos, host):
        super().__init__()
        self.data = {"update" : False}
        self.topics_qos = topics_qos
        # not generalized, need to re-look
        self.callback_functions = {"load_forecast" : self.on_msg_received,
                                   "pv_forecast_data": self.on_msg_received}
        logger.info("Initializing optimization controller")
        self.mqtt = MQTTClient(str(host), 1883)
        self.mqtt.subscribe(self.topics_qos, self.callback_functions)
        if not self.mqtt.subscribe_ack_wait():
            logger.error("Topic subscribe missing ack")
        logger.info("successfully subscribed")

    def on_msg_received(self, payload):
        logger.info("Load data received : " + payload)
        data = json.loads(payload)
        self.data.update(data)
        self.data["update"] = True

    def data_updated(self):
        while not self.data["update"]:
            time.sleep(0.5)
        new_data = self.data.copy()
        new_data.pop("update", None)
        self.data["update"] = False
        return new_data