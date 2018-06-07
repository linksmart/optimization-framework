"""
Created on Jun 07 15:49 2018

@author: nishit
"""
import logging
import threading

import time

from IO.MQTTClient import MQTTClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class DataPublisher(threading.Thread):

    def __init__(self, host, port, topic, qos):
        super().__init__()
        self.host = host
        self.topic = topic
        self.qos = qos
        logger.info("Initializing data publisher thread for topic "+str(self.topic))
        self.mqtt = MQTTClient(str(self.host), port)

    def join(self, timeout=None):
        super(DataPublisher, self).join(timeout)

    def Stop(self):
        if self.isAlive():
            self.join()

    def run(self):
        """Get data from internet or any other source"""
        while True:
            data = "test"+str(time.time())  # test data
            try:
                logger.info("Sending results to this topic: " + self.topic)
                self.mqtt.publish(self.topic, data, True)
                logger.debug("Results published")
            except Exception as e:
                logger.error(e)
            time.sleep(60)


