"""
Created on Aug 03 16:44 2018

@author: nishit
"""
from optimization.baseDataReceiver import BaseDataReceiver

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class SoCValueDataReceiver(BaseDataReceiver):

    def __init__(self, internal, topic_params, config, generic_name, id, buffer, dT):
        self.generic_name = "SoC_Value"
        super().__init__(internal, topic_params, config, self.generic_name, id, buffer, dT, False)

    def preprocess_data(self, base, name, value, unit):
        return value
