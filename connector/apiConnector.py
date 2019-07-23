"""
Created on Mär 18 10:31 2019

@author: nishit
"""
import datetime
import time
import json
import threading
from abc import abstractmethod
from queue import Queue
from random import randrange

import requests
from senml import senml

from IO.MQTTClient import MQTTClient

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class ApiConnector:

    def __init__(self, url, config, house, name):
        logger.info(":")
        self.buffer = None
        self.config = config
        self.pub_prefix = config.get("IO", "pub.topic.prefix") + str(house) + "/"
        self.name = name
        self.url = url
        self.q = Queue()
        logger.info(url)
        self.mqtt_client = self.init_mqtt()
        self.topic = config.get(house, "url.topic", fallback=None)
        self.topic = self.pub_prefix + self.topic
        self.publish_freq = int(config.get(house, "pub.freq", fallback=600))
        self.data_thread = threading.Thread(target=self.fetch_data, args=(self.q, 23, 30))
        self.data_thread.start()
        self.publish_thread = threading.Thread(target=self.publish_data, args=(self.q, self.publish_freq))
        self.publish_thread.start()

    def fetch_data_api(self):
        try:
            logger.debug(self.url)
            data = requests.get(self.url)
            if data:
                data = data.json()
                return data
            else:
                return None
        except Exception as e:
            logger.error(str(e))
            return None

    @abstractmethod
    def update_url(self):
        pass

    @abstractmethod
    def extract_data(self, raw_data):
        pass

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

    def to_senml(self, t, v, u, n):
        meas = senml.SenMLMeasurement()
        meas.time = int(t)
        meas.value = v
        meas.unit = u
        meas.name = n
        return meas

    def get_delay_time(self, hour, min):
        date = datetime.datetime.now()
        requestedTime = datetime.datetime(date.year, date.month, date.day, hour, min, 0)
        if requestedTime < date:
            requestedTime = requestedTime + datetime.timedelta(days=1)
        return requestedTime.timestamp() - date.timestamp()

    def fetch_data(self, q, hr, min):
        """Data fetch thread. Runs at 22:30 every day"""
        while True:
            try:
                self.update_url()
                data = self.fetch_data_api()
                if data is not None:
                    data_list = self.extract_data(data)
                    meas_list = []
                    for row in data_list:
                        meas = self.to_senml(row[0], row[1], row[2], self.name)
                        meas_list.append(meas)
                    logger.info("length of data = "+str(len(meas_list)))
                    doc = senml.SenMLDocument(meas_list)
                    json_data = doc.to_json()
                    json_data = json.dumps(json_data)
                    q.put(json_data)
                delay = self.get_delay_time(hr, min)
                time.sleep(delay)
            except Exception as e:
                logger.error(e)
                time.sleep(10)

    def publish_data(self, q, frequency):
        while True:
            start_time = time.time()
            try:
                if not q.empty():
                    data = q.get()
                    self.buffer = data
                    q.task_done()
            except Exception as e:
                logger.error("q read error "+ str(e))
                time.sleep(10)
            try:
                if self.buffer:
                    self.mqtt_client.publish(topic=self.topic, message=self.buffer, waitForAck=True, qos=1)
                    logger.debug("Results published on this topic: " + self.topic)
                    delay_time = frequency - (time.time() - start_time)
                    if delay_time > 0:
                        time.sleep(delay_time)
            except Exception as e:
                logger.error("Error pub data "+str(e))
                time.sleep(10)