"""
Created on Jun 27 17:34 2018

@author: nishit
"""
import json
import logging

import os

from IO.dataPublisher import DataPublisher


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class MockDataPublisher(DataPublisher):

    def __init__(self, topic_params, config):
        super().__init__(topic_params, config, 10000)
        self.flag = True
        self.file_path = os.path.join("/usr/src/app", "prediction", "USA_AK_King.Salmon.703260_TMY2.csv")

    def get_data(self):
        if self.flag:
            with open(self.file_path) as f:
                data = json.dumps(f.readlines())
            self.flag = False
            return data
        else:
            return "{}"