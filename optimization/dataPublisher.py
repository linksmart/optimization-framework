"""
Created on Jun 07 15:49 2018

@author: nishit
"""
import datetime
import json
import logging
import threading

import time
from queue import Queue
from random import randrange

from IO.MQTTClient import MQTTClient
from IO.ZMQClient import ZMQClient
from IO.radiation import Radiation

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class DataPublisher(threading.Thread):

    #channel = ["MQTT", "ZMQ"]

    def __init__(self, topic_params, config):
        super().__init__()
        self.config = config
        self.channel = config.get("IO", "channel")
        self.topic_params = topic_params
        self.pv_data = {}
        self.load_data = {}
        self.stopRequest = threading.Event()
        if self.channel == "MQTT":
            self.init_mqtt()
        elif self.channel == "ZMQ":
            self.init_zmq()

        #  init pv data source
        if topic_params["topic"] == "forecast/pv":
            city = "Bonn, Germany"
            radiation = Radiation(city, True)
            self.q = Queue(maxsize=0)
            self.pv_thread = threading.Thread(target=self.get_pv_data_from_source, args=(radiation, self.q))
            self.pv_thread.start()
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
            if self.topic_params["topic"] == "forecast/pv":
                #  check if new data is available
                if not self.q.empty():
                    try:
                        new_data = self.q.get_nowait()
                        self.q.task_done()
                        self.pv_data = new_data
                    except Exception:
                        logger.debug("Queue empty")
                logger.debug("extract pv data")
                data = self.extract_1day_data()
                logger.debug(str(data))
            else:
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

    def get_pv_data_from_source(self, radiation, q):
        """PV Data fetch thread. Runs at 23:30 every day"""
        while True:
            try:
                logger.info("Fetching pv data from radiation api")
                data = radiation.get_data()
                pv_data = json.loads(data)
                q.put(pv_data)
                delay = self.getDelayTime(23, 30)
                time.sleep(delay)
            except Exception as e:
                logger.error(e)

    def currentHour(self):
        date = datetime.datetime.now()
        currentHour = datetime.datetime(datetime.datetime.now().year, date.month, date.day, date.hour, 0) + \
            datetime.timedelta(hours=1)
        logger.debug(currentHour.hour)
        return int(currentHour.hour)

    def getDelayTime(self, hour, min):
        date = datetime.datetime.now()
        requestedTime = datetime.datetime(datetime.datetime.now().year, date.month, date.day, hour, min, 0)
        return requestedTime.timestamp() - time.time()

    def extract_1day_data(self):
        currenthr = self.currentHour()
        i = 0
        flag = False
        data = {}
        for row in self.pv_data:
            date = row["date"]
            hr = int(date.split(" ")[1].split(":")[0])
            if currenthr == hr:
                flag = True
            if flag and i < 24:
                data[i] = float(row["pv_output"])
                i = i + 1
            if i > 23:
                break
        return json.dumps({"P_PV_Forecast": data})

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
