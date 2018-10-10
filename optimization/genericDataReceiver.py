"""
Created on Aug 10 12:11 2018

@author: nishit
"""
import logging

from optimization.baseDataReceiver import BaseDataReceiver

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class GenericDataReceiver(BaseDataReceiver):

    def __init__(self, internal, topic_params, config, generic_name, id):
        super().__init__(internal, topic_params, config, generic_name, id)
        self.generic_name = generic_name

    def unit_value_change(self, value, unit):
        return value