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

class MockPLoadDataPublisher(DataPublisher):

    def __init__(self, topic_params, config):
        super().__init__(False, topic_params, config, 1)
        self.flag = True
        self.file_path = os.path.join("/usr/src/app", "mock_data", "USA_AK_King.Salmon.703260_TMY2.csv")
        self.index = 1

    def get_data(self):
        if self.flag:
            with open(self.file_path) as f:
                data = f.readlines()
                if self.index < len(data):
                    data = data[self.index]
                    data = json.dumps([data])
                    self.index += 1
                else:
                    self.flag = False
                    data = {}
            return data
        else:
            return "{}"