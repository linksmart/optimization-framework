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
logger = MessageLogger.get_logger_parent()


class RawLoadDataReceiver(DataReceiver):

    def __init__(self, topic_params, config, buffer, training_data_size, save_path, topic_name, id):
        self.file_path = save_path
        redisDB = RedisDB()
        try:
            super().__init__(False, topic_params, config, [], id)
        except Exception as e:
            redisDB.set("Error mqtt" + self.id, True)
            logger.error(e)
        self.buffer_data = []
        self.buffer = buffer
        self.training_data_size = training_data_size
        self.current_minute = None
        self.id = id
        self.sum = 0
        self.count = 0
        self.minute_data = []
        self.topic_name = topic_name
        self.load_data()
        self.file_save_thread = threading.Thread(target=self.save_to_file_cron)
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
            self.data_update = True
            self.minute_data.extend(mod_data)
            #logger.info("raw data size = " + str(len(mod_data)))
        except Exception as e:
            logger.error(e)

    def save_to_file(self):
        try:
            logger.info("Saving raw data to file "+str(self.file_path))
            old_data = RawDataReader.read_from_file(self.file_path, self.topic_name)
            for item in self.minute_data:
                line = ','.join(map(str, item[:2])) + "\n"
                old_data.append(line)
            old_data = old_data[-10080:] # 7 days data
            update_data = []
            for i, line in enumerate(old_data):
                c = line.count(",")
                if c == 2:
                    s = line.split(",")
                    m = s[1]
                    mv = m[:-12]
                    mt = m[-12:]
                    l1 = [float(s[0]), float(mv)]
                    l1 = ','.join(map(str, l1[:2])) + "\n"
                    l2 = [float(mt), float(s[2].replace("\n",""))]
                    l2 = ','.join(map(str, l2[:2])) + "\n"
                    update_data.append([i, l1, l2])
                elif c != 1:
                    update_data.append([i, None, None])
            shift = 0
            for d in update_data:
                if d[1] is not None and d[2] is not None:
                    old_data.pop(d[0] + shift)
                    old_data.insert(d[0] + shift, d[1])
                    old_data.insert(d[0] + shift + 1, d[2])
                    shift += 1
                else:
                    old_data.pop(d[0] + shift)
                    shift -= 1
            with open(self.file_path, 'w+') as file:
                    file.writelines(old_data)
            file.close()
            self.minute_data = []
        except Exception as e:
            logger.error("failed to save_to_file "+ str(e))

    def get_raw_data(self, train=False, topic_name=None):
        if train:
            data = RawDataReader.read_from_file(self.file_path, topic_name)
            if len(data) > self.training_data_size:
                data = data[-self.training_data_size:]
            return RawDataReader.format_data(data)
        else:
            data = self.get_data(0, True)
            for item in data:
                self.buffer_data.append(item)
            self.buffer_data = self.buffer_data[-self.buffer:]
            return self.buffer_data

    def get_sleep_secs(self, repeat_hour):
        current_time = datetime.datetime.now()
        current_hour = current_time.hour
        hr_diff = repeat_hour - current_hour%repeat_hour
        next_time = current_time + datetime.timedelta(hours=hr_diff)
        next_time = next_time.replace(minute=0, second=0, microsecond=0)
        time_diff = next_time - current_time
        return time_diff.total_seconds()

    def save_to_file_cron(self):
        self.logger.debug("Started save file cron")
        while True and not self.stop_request:
            self.save_to_file()
            time.sleep(self.get_sleep_secs(1))

    def load_data(self):
        data = RawDataReader.get_raw_data(self.file_path, self.buffer, self.topic_name)
        self.buffer_data = data.copy()