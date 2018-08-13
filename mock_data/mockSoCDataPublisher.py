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
        super().__init__(topic_params, config, 5)
        self.index = 20

    def get_data(self):
        meas = senml.SenMLMeasurement()
        meas.name = "ESS_SoC_Value"
        meas.value = random.randint(20,100)
        meas.time = time.time()
        return json.dumps(meas.to_json())