"""
Created on Aug 09 14:11 2018

@author: nishit
"""
import json
import logging

import os
import random

import time
from senml import senml

from IO.dataPublisher import DataPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class MockSoCDataPublisher(DataPublisher):

    def __init__(self, topic_params, config):
        super().__init__(False, topic_params, config, 10)
        self.index = 20
        self.value=20

    def get_data(self):
        meas = senml.SenMLMeasurement()
        meas.name = "SoC_Value"
        #meas.value = random.randint(20,100)
        self.value= self.value + 1
        meas.value = self.value
        meas.time = time.time()
        logger.debug("meas: "+str(meas))
        logger.debug("type meas: " + str(type(meas)))
        val={"e":[json.loads(json.dumps(meas.to_json()))]}
        logger.debug("Val: "+str(val))
        val=json.dumps(val)
        logger.debug("Sent MQTT:"+str(val))
        return val