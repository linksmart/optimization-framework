"""
Created on Aug 03 16:44 2018

@author: nishit
"""
import json
import logging

from IO.dataReceiver import DataReceiver

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class ESSDataReceiver(DataReceiver):

    def __init__(self, internal, topic_params, config):
        super().__init__(internal, topic_params, config)

    def on_msg_received(self, payload):
        raw_data = json.loads(payload)
        formated_data = self.add_formated_data(raw_data)
        self.data.append(formated_data)
        self.data_update = True
        logger.info("ess data received")

    def add_formated_data(self, data):
        # format as per requirement, for here it should be like {"ESS_SoC_Value": {0: 0.12}}
        value = data/100
        # value = data["value"]
        # assuming the value is a float value
        new_data = {0: value}
        return new_data

