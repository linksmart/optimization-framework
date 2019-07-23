"""
Created on Aug 10 12:11 2018

@author: nishit
"""
from optimization.baseDataReceiver import BaseDataReceiver

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class GenericDataReceiver(BaseDataReceiver):

    def __init__(self, internal, topic_params, config, generic_name, id, buffer, dT):
        super().__init__(internal, topic_params, config, generic_name, id, buffer, dT, False)
        self.generic_name = generic_name

    def preprocess_data(self, base, name, value, unit):
        return value