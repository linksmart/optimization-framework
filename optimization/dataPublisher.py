"""
Created on Jun 07 15:49 2018

@author: nishit
"""
import json
import logging
import threading

import time
from random import randrange

from IO.MQTTClient import MQTTClient
from IO.ZMQClient import ZMQClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class DataPublisher(threading.Thread):

    #channel = ["MQTT", "ZMQ"]

    def __init__(self, topic_params, config):
        super().__init__()
        self.config = config
        self.channel = config.get("IO", "channel")
        self.topic_params = topic_params
        self.stopRequest = threading.Event()
        if self.channel == "MQTT":
            self.init_mqtt()
        elif self.channel == "ZMQ":
            self.init_zmq()
        logger.info("Initializing data publisher thread for topic " + str(self.topic_params["topic"]))

    def init_mqtt(self):
        self.host = self.config.get("IO", "mqtt.host")
        self.port = self.topic_params["mqtt.port"]
        self.qos = 1
        self.client_id = "client" + str(randrange(100))
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
            #time.sleep(30) # test delay in data receive
            data = self.get_data()  # test data
            if self.channel == "MQTT":
                self.mqtt_publish(data)
            elif self.channel == "ZMQ":
                self.zmq_publish(data)
            time.sleep(30)

    def mqtt_publish(self, data):
        try:
            logger.info("Sending results to mqtt on this topic: " + self.topic_params["topic"])
            self.mqtt.publish(self.topic_params["topic"], data, True)
            logger.debug("Results published")
        except Exception as e:
            logger.error(e)

    def zmq_publish(self, data):
        logger.info("Sending results to zmq on this topic: " + self.topic_params["topic"])
        self.zmq.publish_message(self.topic_params["topic"], data)
        logger.debug("Results published")

    def get_data(self):
        """sample data"""
        data = {'P_Load_Forecast': {
            0: 0.057,
            1: 0.0906,
            2: 0.0906,
            3: 0.070066667,
            4: 0.077533333,
            5: 0.0906,
            6: 0.0906,
            7: 0.10935,
            8: 0.38135,
            9: 1.473716667,
            10: 0.988183333,
            11: 2.4413,
            12: 0.4216,
            13: 0.21725,
            14: 0.4536,
            15: 0.4899,
            16: 0.092466667,
            17: 0.088733333,
            18: 0.0906,
            19: 0.47475,
            20: 0.48255,
            21: 1.051866667,
            22: 1.296316667,
            23: 0.200733333},
        'timestamp':time.time()}

        return json.dumps(data)
