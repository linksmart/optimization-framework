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
        self.prev_data = {"date": datetime.datetime.now(), "val":0}
        self.threshold = 6

    def on_msg_received(self, payload):
        data = json.loads(payload)
        data = RawDataReader.format_data(data)
        for item in data:
            dt = datetime.datetime.strptime(item[0], "%m/%d  %H:%M:%S")
            if not (item[1] == self.prev_data["val"] and (dt - self.prev_data["date"]) < datetime.timedelta(self.threshold)):
                self.prev_data.update({"date": dt, "val": item[1]})
                self.data.append(item)
        self.data_update = True
        self.save_to_file(data)
        logger.info("raw data size = " + str(len(data)))

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
