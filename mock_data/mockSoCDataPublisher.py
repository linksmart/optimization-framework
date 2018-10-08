"""
Created on Aug 09 14:11 2018

@author: nishit
"""
import json
import logging

import os
import random

import time

import math
from senml import senml

from IO.dataPublisher import DataPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class MockSoCDataPublisher(DataPublisher):

    def __init__(self, topic_params, config):
        super().__init__(False, topic_params, config, 11)
        self.value = 25
        self.name = "SoC_Value"

    def get_data(self):
        meas = senml.SenMLMeasurement()
        meas.value = self.value
        meas.time = int(math.floor(time.time()))
        meas.name = self.name
        doc = senml.SenMLDocument([meas])
        val = doc.to_json()
        logger.info(str(type(val)))
        val = json.dumps(val)
        logger.debug("Sent MQTT:"+str(val))
        self.value = self.value + 1
        if self.value > 60:
            self.value = 25
        return val