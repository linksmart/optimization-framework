"""
Created on Okt 19 12:05 2018

@author: nishit
"""
import threading
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from random import randrange

import time

from IO.MQTTClient import MQTTClient
from IO.dataReceiver import DataReceiver

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class RecPub:

    def Stop(self):
        self.rec.exit()
        self.pub.exit()

    @abstractmethod
    def data_formater(self, data):
        pass

    def __init__(self, receiver_params, publisher_workers, config, section):
        self.q = Queue(maxsize=0)
        self.pub = Publisher(config, self.q, publisher_workers, id="none")
        self.rec = Receiver(False, receiver_params, config, self.q, self.data_formater, section, id="none")

class Receiver(DataReceiver):

    def __init__(self, internal, topic_params, config, q, data_formater, section, id):
        self.q = q
        self.data_formater = data_formater
        super().__init__(internal, topic_params, config, id=id, section=section)

    def on_msg_received(self, payload):
        try:
            logger.info("msg rec : "+str(payload))
            data = self.data_formater(payload)
            if len(data) == 0:
                logger.info("No keys found in received data")
            for topic, value in data.items():
                d = {"topic": topic, "data": value}
                self.q.put(d)
        except Exception as e:
            logger.error(e)

class Publisher():

    def __init__(self, config, q, workers, id):
        self.stopRequest = threading.Event()
        self.config = config
        self.q = q
        self.id = id
        self.num_of_workers = workers
        logger.info("number_of_workers = "+ str(self.num_of_workers))
        self.mqtt_clients = self.init_mqtt_clients(self.num_of_workers)
        self.executor = ThreadPoolExecutor(max_workers=self.num_of_workers)
        self.consumer_thread = threading.Thread(target=self.consumer)
        self.consumer_thread.start()

    def init_mqtt_clients(self, n):
        mqtt_clients = []
        if n < 1:
            n = 1
        for i in range(n):
            mqtt_clients.append(self.init_mqtt())
        return mqtt_clients

    def init_mqtt(self):
        try:
            if "pub.mqtt.host" in dict(self.config.items("IO")):
                host = self.config.get("IO", "pub.mqtt.host")
            else:
                host = self.config.get("IO", "mqtt.host")
            port = self.config.get("IO", "mqtt.port")
            client_id = "client_publish" + str(randrange(100000)) + str(time.time()).replace(".","")
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
        i = 0
        while True and not self.stopRequest.is_set():
            #logger.info("q size " + str(self.q.qsize()))
            if not self.q.empty():
                try:
                    #logger.debug("Queue size: " + str(self.q.qsize()))
                    data = self.q.get()
                    if data is not None:
                        client = self.mqtt_clients[i]
                        self.executor.submit(self.publish_data, data, client)
                        self.q.task_done()
                        i += 1
                        if i >= self.num_of_workers:
                            i = 0
                except Exception as e:
                    logger.error("Error in consuming queue "+str(e))
            else:
                time.sleep(2)

    def publish_data(self, data, mqtt_client):
        try:
            topic = data["topic"]
            data = data["data"]
            mqtt_client.publish(topic=topic, message=data, waitForAck=True, qos=1)
            logger.debug("Results published on this topic: " + topic)# + " "+ str(data))
        except Exception as e:
            logger.error("Error pub data "+str(e))

    def exit(self):
        self.stopRequest.set()
        for client in self.mqtt_clients:
            if client is not None:
                client.MQTTExit()
        self.consumer_thread.join()
