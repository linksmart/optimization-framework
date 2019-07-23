"""
Created on Aug 10 14:01 2018

@author: nishit
"""
import json
import random

import time

import math

from senml import senml

from IO.dataPublisher import DataPublisher

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class MockGenericDataPublisher(DataPublisher):

    def __init__(self, config, mock_params):
        topic_params = mock_params["mqtt_topic"]
        pub_frequency = mock_params["pub_frequency_sec"]
        super().__init__(False, topic_params, config, pub_frequency)
        self.generic_name = mock_params["section"]
        self.length = mock_params["horizon_steps"]
        self.delta_time = mock_params["delta_time_sec"]
        self.source = "random"
        if "mock_source" in mock_params.keys():
            self.source = mock_params["mock_source"]
        if self.source == "file":
            file_path = mock_params["mock_file_path"]
            self.is_timed = False
            self.file_lines = self.read_file_data(file_path)
            self.file_index = 0
            self.file_length = len(self.file_lines)
        elif self.source == "random":
            self.is_timed = False
            self.rand_min = mock_params["mock_random_min"]
            self.rand_max = mock_params["mock_random_max"]
            self.data_type = mock_params["mock_data_type"]
        elif self.source == "constant":
            self.constant_value = mock_params["mock_constant"]

    def get_data(self):
        try:
            if self.source == "constant":
                val = self.constant_value
                logger.debug("Sent MQTT:" + str(val))
                return val
            else:
                meas_list = []
                current_time = int(math.floor(time.time()))
                if self.source == "file":
                    vals = self.get_file_line(current_time)
                    logger.debug("Length: " + str(self.length))
                    if len(vals) < self.length:
                        logger.error(str(self.generic_name) + " mock file has invalid data. Less values than horizon_step")
                        return None
                elif self.source == "random":
                    vals = self.get_random_floats()
                    logger.debug("Vals: "+str(vals))
                logger.debug("Length: " + str(self.length))
                prev_time = 0
                for index in range(self.length):
                    meas = senml.SenMLMeasurement()
                    if self.is_timed:
                        meas.value = vals[index][1]
                        if prev_time > vals[index][0]:
                            meas.time = prev_time + self.delta_time
                        else:
                            meas.time = int(vals[index][0])
                        prev_time = meas.time
                    else:
                        meas.value = vals[index]
                        meas.time = int(current_time)
                    meas.name = self.generic_name
                    meas_list.append(meas)
                    current_time += self.delta_time
                doc = senml.SenMLDocument(meas_list)
                val = doc.to_json()
                val = json.dumps(val)
                logger.debug("Sent MQTT:" + str(val))
                return val
        except Exception as e:
            logger.error(e)

    def read_file_data(self, file_path):
        with open(file_path, "r") as f:
            file_lines = f.readlines()
        logger.debug("file_lines: "+str(file_lines))
        if any(";" in s for s in file_lines):
            timed_vals = []
            # format the file according to val;time
            self.is_timed = True
            for line in file_lines:
                line = line.replace("\n", "")
                vals = line.strip().split(";")
                val = vals[0]
                val = float(val.replace(",", "."))
                time = vals[1]
                time = float(time.replace(",", "."))
                timed_vals.append([time, val])
            timed_vals.sort(key=lambda x: x[0])
            timed_vals = self.expand_and_resample(timed_vals, self.delta_time)
            return timed_vals
        else:
            vals = []
            for line in file_lines:
                line = line.replace("\n","")
                val = float(line.replace(",", "."))
                vals.append(val)
            return vals

    def get_file_line(self, current_time):
        try:
            if self.is_timed:
                # find next closest timestamp
                self.file_index = self.find_closest_timestamp_index(current_time)
            if self.file_index >= self.file_length:
                self.file_index = 0
            line = self.file_lines[self.file_index:(self.file_index + self.length)]
            if self.file_index + self.length > self.file_length:
                line.extend(self.file_lines[:self.file_length-(self.file_index + self.length)])
            end = self.file_index + self.length
            line = self.file_lines[self.file_index:end]
            if end > self.file_length:
                end = end - self.file_length
                q = int(end / self.file_length)
                r = int(end % self.file_length)
                for j in range(q):
                    line.extend(self.file_lines[:])
                line.extend(self.file_lines[:r])
            logger.debug("line: "+str(line))
            self.file_index = self.length + self.file_index
            return line
        except Exception as e:
            logger.error("file line read exception "+str(e))

    def find_closest_timestamp_index(self, current_timestamp):
        if current_timestamp < self.file_lines[0][0] or current_timestamp > self.file_lines[self.file_length - 1][0]:
            return self.file_index
        else:
            return int(math.floor((current_timestamp - self.file_lines[0][0]) / self.delta_time))

    def get_random_floats(self):
        if self.data_type == "float":
            return [round(random.uniform(self.rand_min, self.rand_max), 6) for _ in range(self.length)]
        else:
            return [random.randrange(self.rand_min, self.rand_max+1) for _ in range(self.length)]

    def expand_and_resample(self, raw_data, dT):
        step = float(dT)
        j = len(raw_data) - 1
        new_data = []
        if j > 0:
            start_time = raw_data[j][0]
            start_value = raw_data[j][1]
            new_data.append([start_time, start_value])
            prev_time = start_time
            prev_value = start_value
            required_diff = step
            j -= 1
            while j >= 0:
                end_time = raw_data[j][0]
                end_value = raw_data[j][1]
                diff_sec = prev_time - end_time
                if diff_sec >= required_diff:
                    ratio = required_diff / diff_sec
                    inter_time = prev_time - required_diff
                    inter_value = prev_value - (prev_value - end_value) * ratio
                    new_data.append([inter_time, inter_value])
                    prev_time = inter_time
                    prev_value = inter_value
                    required_diff = step
                else:
                    required_diff -= diff_sec
                    prev_time = end_time
                    prev_value = end_value
                    j -= 1
        else:
            new_data = raw_data
        new_data.reverse()
        return new_data