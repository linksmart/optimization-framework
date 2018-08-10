"""
Created on Aug 10 14:01 2018

@author: nishit
"""
import json
import logging
import random

import time
from senml import senml

from IO.dataPublisher import DataPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class MockGenericDataPublisher(DataPublisher):

    def __init__(self, topic_params, config, generic_name):
        super().__init__(topic_params, config, 5)
        self.generic_name = generic_name

    def get_data(self):
        meas = senml.SenMLMeasurement()
        meas.name = self.generic_name
        meas.value = random.random()
        meas.time = time.time()
        return json.dumps(meas.to_json())