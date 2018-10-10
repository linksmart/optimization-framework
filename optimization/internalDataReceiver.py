"""
Created on Jun 27 18:14 2018

@author: nishit
"""
import json
import logging

from IO.dataReceiver import DataReceiver

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class InternalDataReceiver(DataReceiver):

    def __init__(self, topic_params, config, id):
        super().__init__(True, topic_params, config, id=id)

    def on_msg_received(self, payload):
        logger.debug("Data received : " + payload)
        data = json.loads(payload)
        self.data.update(self.add_formated_data(data))
        logger.info(self.data)
        self.data_update = True

    def add_formated_data(self, data={}):
        new_data = {}
        for k, v in data.items():
            if isinstance(v, dict):
                v = self.change_index_to_integer(v)
                new_data[k] = v
            else:
                new_data[k] = {None: float(v)}
        return new_data

    def change_index_to_integer(self, data):
        new_data = {}
        for k, v in data.items():
            if k.isdigit():
                new_data[int(k)] = v
            else:
                new_data[k] = v
        return new_data