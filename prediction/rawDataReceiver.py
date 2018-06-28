"""
Created on Jun 27 18:27 2018

@author: nishit
"""
import json
import logging

from IO.dataReceiver import DataReceiver

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class RawDataReceiver(DataReceiver):

    def __init__(self, topic_params, config):
        super().__init__(topic_params, config)

    def on_msg_received(self, payload):
        data = json.loads(payload)
        self.data = self.add_formated_data(data)
        self.data_update = True
        logger.info("raw data size = " + str(len(data)))

    def add_formated_data(self, data=[]):
        new_data = []
        i = 0
        for row in data:
            cols = row.replace('\n', '').strip().split(",")
            if not i == 0:
                dateTime = cols[0]
                cols = cols[1:]
                cols = list(map(float, cols))
                cols.insert(0, dateTime)
            if i < 3:
                logger.info(cols)
                i += 1
            new_data.append(cols)
        return new_data