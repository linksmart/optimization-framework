"""
Created on Jun 27 18:27 2018

@author: nishit
"""
import json

import datetime
import threading
import time

from IO.dataReceiver import DataReceiver
from IO.redisDB import RedisDB
from prediction.rawDataReader import RawDataReader

from utils_intern.messageLogger import MessageLogger
from utils_intern.utilFunctions import UtilFunctions

logger = MessageLogger.get_logger_parent()


class RawLoadDataReceiver(DataReceiver):

    def __init__(self, topic_params, config, buffer, save_path, topic_name, id, load_file_data, max_file_size_mins):
        self.file_path = save_path
        redisDB = RedisDB()
        try:
            super().__init__(False, topic_params, config, [], id)
        except Exception as e:
            redisDB.set("Error mqtt" + self.id, True)
            logger.error(e)
        self.buffer_data = []
        self.buffer = buffer
        self.current_minute = None
        self.id = id
        self.sum = 0
        self.count = 0
        self.minute_data = []
        self.topic_name = topic_name
        self.max_file_size_mins = max_file_size_mins
        self.save_cron_freq = config.getint("IO", "raw.data.file.save.frequency.sec", fallback=3600)

        if load_file_data:
            self.load_data()
        self.file_save_thread = threading.Thread(target=self.save_to_file_cron, args=(self.save_cron_freq,))
        self.file_save_thread.start()

    def on_msg_received(self, payload):
        try:
            data = json.loads(payload)
            data = RawDataReader.format_data(data)
            #logger.debug("data raw "+str(data))
            #logger.debug("current min "+str(self.current_minute))
            mod_data = []
            for item in data:
                dt = datetime.datetime.fromtimestamp(item[0]).replace(second=0, microsecond=0)
                if self.current_minute is None:
                    self.current_minute = dt
                if dt == self.current_minute:
                    self.sum += item[1]
                    self.count += 1
                else:
                    if self.count > 0:
                        val = self.sum/self.count
                        row = [self.current_minute.timestamp(), val]
                        self.data.append(row)
                        mod_data.append(row)
                    self.current_minute = dt
                    self.sum = item[1]
                    self.count = 1
            if len(mod_data) > 0:
                self.data_update = True
            self.minute_data.extend(mod_data)
            #logger.info("raw data size = " + str(len(mod_data)))
        except Exception as e:
            logger.error(e)

    def get_raw_data(self):
        data = self.get_data(0, True)
        self.logger.debug(str(self.topic_name)+"value from mqtt for prediction input = "+str(data))
        for item in data:
            self.buffer_data.append(item)
        self.buffer_data = self.buffer_data[-self.buffer:]
        return self.buffer_data

    def save_to_file_cron(self, repeat_seconds):
        self.logger.debug("Started save file cron")
        while True and not self.stop_request:
            self.minute_data = RawDataReader.save_to_file(self.file_path, self.topic_name, self.minute_data,
                                                          self.max_file_size_mins)
            time.sleep(UtilFunctions.get_sleep_secs(0,0,repeat_seconds))

    def load_data(self):
        data = RawDataReader.get_raw_data(self.file_path, self.topic_name, self.buffer)
        self.buffer_data = data.copy()