"""
Created on Aug 09 14:11 2018

@author: nishit
"""
import logging

import os

from IO.dataPublisher import DataPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class MockSoCDataPublisher(DataPublisher):

    def __init__(self, topic_params, config):
        super().__init__(topic_params, config, 5)
        self.flag = True
        self.index = 0

    def get_data(self):
        if self.flag:
            if self.index < 100:
                self.index += 1
                return self.index
            else:
                self.flag = False
                return 1
        else:
            return 1