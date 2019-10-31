"""
Created on Sep 19 15:45 2019

@author: nishit
"""
import configparser
import threading
from abc import abstractmethod
from queue import Queue
from random import randrange

import time

from IO.MQTTClient import MQTTClient
from IO.dataReceiver import DataReceiver

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class SummationPub():

    def Stop(self):
        self.rec.exit()
        self.pub.exit()

    @abstractmethod
    def data_formater(self, data):
        pass

    @abstractmethod
    def sum_data(self):
        pass

    def __init__(self, receiver_params, config):
        self.q = Queue(maxsize=0)
        self.pub = Publisher(config, self.q)
        self.rec = Receiver(True, receiver_params, config, self.data_formater, id="none")


class Receiver(DataReceiver):

    def __init__(self, internal, topic_params, config, data_formater, id):
        self.data_formater = data_formater
        super().__init__(internal, topic_params, config, id=id, prepare_topic_qos=False, sub_pub=True)

    def on_msg_received(self, payload):
        try:
            logger.info("msg rec : " + str(payload))
            data = self.data_formater(payload)
            if len(data) == 0:
                logger.info("No keys found in received data")
            self.data.update(data)
            self.data_update = True
            self.last_time = time.time()
        except Exception as e:
            logger.error(e)

class Publisher():

    def __init__(self, config, q):
        self.stopRequest = threading.Event()
        self.config = config
        self.q = q
        self.mqtt_client = self.init_mqtt()
        self.consumer_thread = threading.Thread(target=self.consumer)
        self.consumer_thread.start()

    def init_mqtt(self):
        try:
            if "pub.mqtt.host" in dict(self.config.items("IO")):
                host = self.config.get("IO", "pub.mqtt.host")
            else:
                host = self.config.get("IO", "mqtt.host")
            port = self.config.get("IO", "mqtt.port")
            client_id = "client_publish" + str(randrange(100000)) + str(time.time()).replace(".", "")
            mqtt = MQTTClient(str(host), port, client_id,
                              username=self.config.get("IO", "mqtt.username", fallback=None),
                              password=self.config.get("IO", "mqtt.password", fallback=None),
                              ca_cert_path=self.config.get("IO", "mqtt.ca.cert.path", fallback=None),
                              set_insecure=bool(self.config.get("IO", "mqtt.insecure.flag", fallback=False)))
            return mqtt
        except Exception as e:
            logger.error(e)
            raise e

    def consumer(self):
        while True and not self.stopRequest.is_set():
            if not self.q.empty():
                try:
                    logger.debug("Queue size: " + str(self.q.qsize()))
                    data = self.q.get()
                    if data is not None:
                        self.publish_data(data)
                except Exception as e:
                    logger.error("Error in consuming queue " + str(e))
            else:
                time.sleep(2)

    def publish_data(self, data):
        try:
            topic = data["topic"]
            data = data["data"]
            self.mqtt_client.publish(topic=topic, message=data, waitForAck=True, qos=1)
            logger.debug("Results published on this topic: " + topic)
        except Exception as e:
            logger.error("Error pub data " + str(e))

    def exit(self):
        self.stopRequest.set()
        self.mqtt_client.MQTTExit()
        self.consumer_thread.join()
