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

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class DataPublisher(threading.Thread):

    def __init__(self, host, port, topic, qos):
        super().__init__()
        self.host = host
        self.topic = topic
        self.qos = qos
        self.client_id = "client" + str(randrange(100))
        logger.info("Initializing data publisher thread for topic "+str(self.topic))
        self.mqtt = MQTTClient(str(self.host), port, self.client_id)

    def join(self, timeout=None):
        super(DataPublisher, self).join(timeout)

    def Stop(self):
        self.mqtt.MQTTExit()
        if self.isAlive():
            self.join()

    def run(self):
        """Get data from internet or any other source"""
        while True:
            time.sleep(30)
            data = self.get_data()  # test data
            try:
                logger.info("Sending results to this topic: " + self.topic)
                self.mqtt.publish(self.topic, data, True)
                logger.debug("Results published")
            except Exception as e:
                logger.error(e)



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
        'Q_Load_Forecast': {
            0: 0.0,
            1: 0.0,
            2: 0.0,
            3: 0.0,
            4: 0.0,
            5: 0.0,
            6: 0.0,
            7: 0.0,
            8: 0.0,
            9: 0.0,
            10: 0.0,
            11: 0.0,
            12: 0.0,
            13: 0.0,
            14: 0.0,
            15: 0.0,
            16: 0.0,
            17: 0.0,
            18: 0.0,
            19: 0.0,
            20: 0.0,
            21: 0.0,
            22: 0.0,
            23: 0.0},
        'timestamp':time.time()}

        return json.dumps(data)