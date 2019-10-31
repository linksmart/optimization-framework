"""
Created on Aug 13 11:03 2018

@author: nishit
"""
import json
from abc import ABC, abstractmethod

import datetime
import time
from math import floor

from senml import senml

from IO.dataReceiver import DataReceiver
from IO.redisDB import RedisDB
from utils_intern.messageLogger import MessageLogger

class BaseDataReceiver(DataReceiver, ABC):

    def __init__(self, internal, topic_params, config, generic_name, id, buffer, dT, base_value_flag):
        redisDB = RedisDB()
        self.logger = MessageLogger.get_logger(__name__, id)
        self.generic_name = generic_name
        self.buffer = buffer
        self.dT = dT
        self.base_value_flag = base_value_flag
        if "detachable" in topic_params.keys():
            self.detachable = topic_params["detachable"]
        else:
            self.detachable = False
        if "reuseable" in topic_params.keys():
            self.reuseable = topic_params["reuseable"]
        else:
            self.reuseable = False
        self.start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        self.total_steps_in_day = floor(24 * 60 * 60 / self.dT)
        self.current_day_index = 0
        self.number_of_bucket_days = int(buffer / self.total_steps_in_day)
        self.bucket_index = False
        self.length = 1
        try:
            super().__init__(internal, topic_params, config, id=id)
        except Exception as e:
            redisDB.set("Error mqtt" + self.id, True)
            self.logger.error(e)

    def on_msg_received(self, payload):
        try:
            self.start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            senml_data = json.loads(payload)
            formated_data = self.add_formated_data(senml_data)
            self.data.update(formated_data)
            self.data_update = True
            self.last_time = time.time()
        except Exception as e:
            self.logger.error(e)

    def add_formated_data(self, json_data):
        doc = None
        try:
            doc = senml.SenMLDocument.from_json(json_data)
        except Exception as e:
            pass
        if not doc:
            try:
                meas = senml.SenMLMeasurement.from_json(json_data)
                doc = senml.SenMLDocument([meas])
            except Exception as e:
                pass
        if doc:
            base_data = doc.base
            bn, bu = None, None
            if base_data:
                bn = base_data.name
                bu = base_data.unit
            data = {}
            raw_data = []
            doc.measurements = sorted(doc.measurements, key=lambda x: x.time)
            if len(doc.measurements) > 0:
                self.length = len(doc.measurements)
                for meas in doc.measurements:
                    n = meas.name
                    u = meas.unit
                    v = meas.value
                    t = meas.time
                    t = self.time_conversion(t)
                    if not u:
                        u = bu
                    # dont check bn
                    if not n:
                        n = self.generic_name
                    try:
                        processed_value = self.preprocess_data(bn, n, v, u)
                        if processed_value is not None and processed_value is not {}:
                            raw_data.append([t, processed_value])
                    except Exception as e:
                        self.logger.error("error " + str(e) + "  n = " + str(n))
                #self.logger.debug("data: " + str(data))
                raw_data = self.expand_and_resample(raw_data, self.dT)
                if len(raw_data) > 0:
                    bucket = self.time_to_bucket(raw_data[0][0])
                    for row in raw_data:
                        bucket_key = str(self.current_day_index) + "_" + str(bucket)
                        bucket += 1
                        if bucket >= self.total_steps_in_day:
                            bucket = 0
                            self.current_day_index += 1
                            if self.current_day_index >= self.number_of_bucket_days:
                                self.current_day_index = 0
                        data[bucket_key] = row[1]
            return data
        return {}

    @abstractmethod
    def preprocess_data(self, base, name, value, unit):
        return value

    def iterative_init(self, d, v):
        if len(v) <= 0:
            return d
        d = self.iterative_init({v[-1]: d}, v[:-1])
        return d

    def get_bucket_aligned_data(self, bucket, steps, wait_for_data=True, check_bucket_change=True):
        bucket_requested = bucket
        self.logger.info("Get "+str(self.generic_name)+" data for bucket = "+str(bucket_requested))
        bucket_available = True
        if self.base_value_flag:
            final_data = self.iterative_init({}, self.generic_name.split("/"))
        else:
            final_data = {self.generic_name: {}}

        if self.detachable and self.reuseable:
            data = self.get_data(require_updated=2)
        elif self.detachable:
            data = self.get_data(require_updated=2, clearData=True)
        elif self.reuseable:
            data = self.get_data(require_updated=1)
        elif wait_for_data:
            data = self.get_data(require_updated=0)
        else:
            data = self.get_data(require_updated=2)

        self.logger.debug(str(self.generic_name)+ " data from mqtt is : "+ json.dumps(data, indent=4))
        if steps > self.length:
            steps = self.length
        day = None
        if len(data) >= steps:
            for i in reversed(range(self.number_of_bucket_days+1)):
                key = str(i) + "_" + str(bucket)
                if key in data.keys():
                    day = str(i)
                    break
            if day is None:
                bucket_available = False
            else:
                new_data = {}
                index = 0
                while len(new_data) < steps:
                    bucket_key = day + "_" + str(bucket)
                    if bucket_key in data.keys():
                        new_data[index] = data[bucket_key]
                        index += 1
                    bucket += 1
                    if bucket >= self.total_steps_in_day:
                        bucket = 0
                        day_i = int(day) + 1
                        if day_i >= self.number_of_bucket_days:
                            day_i = 0
                        day = str(day_i)
                if self.base_value_flag:
                    for k, v in new_data.items():
                        if isinstance(v, dict):
                            final_data.update(v)
                else:
                    final_data = {self.generic_name: new_data}
        if check_bucket_change:
            new_bucket = self.time_to_bucket(datetime.datetime.now().timestamp())
            if new_bucket > bucket_requested:
                self.logger.debug("bucket changed from " + str(bucket_requested) +
                                  " to " + str(new_bucket) + " due to wait time for " + str(self.generic_name))
                final_data, bucket_available, _ = self.get_bucket_aligned_data(new_bucket, steps, wait_for_data=False, check_bucket_change=False)
        return final_data, bucket_available, self.last_time

    def time_conversion(self, time):
        t = str(time)
        l = len(t)
        if "." in t:
            l = t.find(".")
        if l > 10:
            new_t = time / (10 ** (l - 10))
            return new_t
        else:
            return time

    def time_to_bucket(self, time):
        bucket = floor((time - self.start_of_day) / self.dT)
        if bucket > self.total_steps_in_day:
            bucket = self.total_steps_in_day
        elif bucket < 0:
            self.logger.info("Received data is of older timestamp = "+str(time)+" than start of today = "+str(self.start_of_day))
            bucket = bucket%self.total_steps_in_day
        return bucket

    def expand_and_resample(self, raw_data, dT):
        if self.expand_data_valid(raw_data):
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
        else:
            new_data = raw_data
        return new_data

    def expand_data_valid(self, raw_data):
        try:
            if isinstance(raw_data, list):
                if len(raw_data) > 0:
                    sample = raw_data[0]
                    if len(sample) == 2:
                        if (isinstance(sample[0], float) or isinstance(sample[0], int)) and (isinstance(sample[1], float) or isinstance(sample[1], int)):
                            return True
            return False
        except Exception:
            return False

    def get_current_bucket_data(self, steps, wait_for_data=True, check_bucket_change=True):
        bucket = self.time_to_bucket(datetime.datetime.now().timestamp())
        self.logger.debug("current b = "+str(bucket))
        return self.get_bucket_aligned_data(bucket, steps, wait_for_data, check_bucket_change)