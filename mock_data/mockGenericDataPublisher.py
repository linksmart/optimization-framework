"""
Created on Aug 10 14:01 2018

@author: nishit
"""
import json
import logging
import random

import time

import math
from senml import senml

from IO.dataPublisher import DataPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class MockGenericDataPublisher(DataPublisher):

    def __init__(self, topic_params, config, generic_name, length, const_value=None):
        super().__init__(False, topic_params, config, 5)
        self.generic_name = generic_name
        self.length = length
        self.const_value = const_value

    def get_data(self):
        meas_list = []
        current_time = int(math.floor(time.time()))
        for index in range(self.length):
            meas = senml.SenMLMeasurement()
            if self.const_value is not None:
                meas.value = self.const_value
            else:
                meas.value = random.random()
            meas.time = int(current_time)
            meas.name = self.generic_name
            meas_list.append(meas)
            current_time += 10
        doc = senml.SenMLDocument(meas_list)
        val = doc.to_json()
        val = json.dumps(val)
        logger.debug("Sent MQTT:" + str(val))
        return val