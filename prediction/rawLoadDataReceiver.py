"""
Created on Jun 27 18:27 2018

@author: nishit
"""
import json
import logging

import datetime

from IO.dataReceiver import DataReceiver
from prediction.rawDataReader import RawDataReader

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class RawLoadDataReceiver(DataReceiver):

    def __init__(self, topic_params, config, buffer, training_data, save_path):
        self.file_path = save_path
        super().__init__(False, topic_params, config, [])
        self.buffer_data = []
        self.buffer = buffer
        self.training_data = training_data
        self.current_minute = None
        self.sum = 0
        self.count = 0

    def on_msg_received(self, payload):
        data = json.loads(payload)
        data = RawDataReader.format_data(data)
        mod_data = []
        for item in data:
            dt = datetime.datetime.fromtimestamp(item[0]).replace(second=0, microsecond=0)
            if self.current_minute is None:
                self.current_minute = dt
            logger.info(str(dt)+" "+str(self.current_minute))
            if dt == self.current_minute:
                self.sum += item[1]
                self.count += 1
            else:
                logger.info("diff "+str(self.count)+str(self.sum))
                if self.count > 0:
                    val = self.sum/self.count
                    row = [self.current_minute.timestamp(), val]
                    self.data.append(row)
                    mod_data.append(row)
                self.current_minute = dt
                self.sum = item[1]
                self.count = 1
        self.data_update = True
        self.save_to_file(mod_data)
        logger.info("raw data size = " + str(len(mod_data)))

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

    def get_raw_data(self, train=False, topic_name=None):
        if train:
            data = RawDataReader.read_from_file(self.file_path, topic_name)
            if len(data) > self.training_data:
                data = data[-self.training_data:]
            return RawDataReader.format_data(data)
        else:
            data = self.get_data(0, True)
            for item in data:
                self.buffer_data.append(item)
            self.buffer_data = self.buffer_data[-self.buffer:]
            return self.buffer_data
