"""
Created on Jun 27 18:27 2018

@author: nishit
"""
import json
import logging

import os

from IO.dataReceiver import DataReceiver

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class RawDataReceiver(DataReceiver):

    def __init__(self, topic_params, config, buffer, training_data, save_path):
        self.file_path = save_path
        super().__init__(topic_params, config, [])
        self.buffer_data = []
        self.buffer = buffer
        self.training_data = training_data

    def on_msg_received(self, payload):
        data = json.loads(payload)
        data = self.add_formated_data(data)
        for item in data:
            self.data.append(item)
        self.data_update = True
        self.save_to_file(data)
        logger.info("raw data size = " + str(len(data)))

    def add_formated_data(self, data=[]):
        new_data = []
        for row in data:
            cols = row.replace('\n', '').strip().split(",")
            dateTime = cols[0]
            cols = cols[1:]
            cols = list(map(float, cols))
            cols.insert(0, dateTime)
            new_data.append(cols)
        return new_data

    def save_to_file(self, data):
        try:
            with open(self.file_path, 'a+') as file:
                for item in data:
                    line = ','.join(map(str, item[:2]))+"\n"
                    file.writelines(line)
            file.close()
        except Exception as e:
            logger.error("failed to save "+ str(e))
        return True

    def read_from_file(self):
        try:
            with open(self.file_path) as file:
                data = file.readlines()
            file.close()
            return data
        except Exception as e:
            logger.error(e)
        return []

    def get_raw_data(self, train=False):
        if train:
            data = self.read_from_file()
            if len(data) > self.training_data:
                data = data[-self.training_data:]
            return self.add_formated_data(data)
        else:
            data = self.get_data(0, True)
            for item in data:
                self.buffer_data.append(item)
            self.buffer_data = self.buffer_data[-self.buffer:]
            return self.buffer_data
