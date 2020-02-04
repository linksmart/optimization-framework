"""
Created on Jan 28 15:18 2020

@author: nishit
"""
import json
from random import randrange

import time

from senml import senml

from IO.MQTTClient import MQTTClient
from utils_intern.messageLogger import MessageLogger

class MonitorPub:

    def __init__(self, config, id):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.id = id
        self.config = config
        self.host = config.get("IO", "mqtt.host")
        self.port = config.getint("IO", "mqtt.port", fallback=1883)
        self.topic_params = json.loads(config.get("IO", "monitor.mqtt.topic"))
        self.topic = self.topic_params["topic"]
        if "mqtt.port" in self.topic_params:
            self.port = int(self.topic_params["mqtt.port"])
        self.qos = 1
        if "qos" in self.topic_params:
            self.qos = int(self.topic_params["qos"])
        self.init_mqtt()

    def init_mqtt(self):
        try:
            client_id = "client_publish" + str(randrange(100000)) + str(time.time()).replace(".", "")
            self.mqtt = MQTTClient(str(self.host), self.port, client_id, id=self.id)
            self.logger.info("successfully subscribed")
        except Exception as e:
            self.logger.error(e)

    def optimization_finished(self, control_frequency):
        msg = self.to_senml(control_frequency)
        self.mqtt.publish(self.topic, msg, qos=self.qos)

    def to_senml(self, value):
        meas = senml.SenMLMeasurement()
        meas.name = self.id
        meas.value = value
        meas.time = int(time.time())
        doc = senml.SenMLDocument([meas])
        return json.dumps(doc.to_json())