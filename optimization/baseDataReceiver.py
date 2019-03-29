"""
Created on Aug 13 11:03 2018

@author: nishit
"""
import json
import logging
from abc import ABC, abstractmethod

import datetime
from math import floor

from senml import senml

from IO.dataReceiver import DataReceiver
from IO.redisDB import RedisDB

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class BaseDataReceiver(DataReceiver, ABC):

    def __init__(self, internal, topic_params, config, generic_name, id, buffer, dT):
        redisDB = RedisDB()
        try:
            super().__init__(internal, topic_params, config, id=id)
        except Exception as e:
            redisDB.set("Error mqtt" + self.id, True)
            logger.error(e)
        self.generic_name = generic_name
        self.buffer = buffer
        self.dT = dT
        self.start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        self.total_steps_in_day = floor(24 * 60 * 60 / self.dT)
        self.current_day_index = 0
        self.number_of_bucket_days = int(buffer / self.total_steps_in_day)
        self.bucket_index = False
        self.length = 1

    def on_msg_received(self, payload):
        try:
            self.start_of_day = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            senml_data = json.loads(payload)
            formated_data = self.add_formated_data(senml_data)
            self.data.update(formated_data)
            self.data_update = True
        except Exception as e:
            logger.error(e)

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
                    if not u:
                        u = bu
                    # dont check bn
                    if not n:
                        n = self.generic_name
                    try:
                        v = self.unit_value_change(v, u)
                        raw_data.append([t, v])
                    except Exception as e:
                        logger.error("error " + str(e) + "  n = " + str(n))
                #logger.debug("data: " + str(data))
                logger.debug("len data before expansion = "+str(len(raw_data)))
                logger.debug("before expansion = "+str(raw_data[0][0])+ " "+ str(raw_data[-1][0]))
                raw_data = self.expand_and_resample(raw_data, self.dT)
                logger.debug("len data after expansion = " + str(len(raw_data)))
                logger.debug("after expansion = "+str(raw_data[0][0])+ " "+ str(raw_data[-1][0]))
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
    def unit_value_change(self, value, unit):
        pass

    def get_bucket_aligned_data(self, bucket, steps):
        logger.info("Get "+str(self.generic_name)+" data for bucket = "+str(bucket))
        bucket_available = True
        final_data = {self.generic_name: {}}
        data = self.get_data()
        if steps > self.length:
            steps = self.length
        day = None
        if len(data) >= steps:
            for i in reversed(range(self.number_of_bucket_days)):
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
                final_data = {self.generic_name: new_data}
        return final_data, bucket_available

    def time_to_bucket(self, time):
        bucket = floor((time - self.start_of_day) / self.dT)
        if bucket > self.total_steps_in_day:
            bucket = self.total_steps_in_day
        elif bucket < 0:
            logger.info("Received data is of older timestamp = "+str(time)+" than start of today = "+str(self.start_of_day))
            bucket = bucket%self.total_steps_in_day
        return bucket

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