"""
Created on Okt 19 11:54 2018

@author: nishit
"""
import json

import time
from senml import senml

from IO.RecPub import RecPub

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class ParserConnector(RecPub):

    def __init__(self, receiver_params, publisher_workers, config, house):
        self.pub_prefix = config.get("IO","pub.topic.prefix") + str(house) + "/"
        self.key_level = int(config.get(house,"key.level"))
        self.key_separator = config.get(house,"key.separator", fallback="/")
        self.data_type = config.get(house, "data.type", fallback="json")
        self.key_map = dict(config.items("KEYS"))
        self.house = house
        self.base = senml.SenMLMeasurement()
        self.base.name = house + "/"
        super().__init__(receiver_params, publisher_workers, config, house)

    def data_formater(self, data):
        if self.data_type == "json":
            data = json.loads(data)
        elif self.data_type == "comma_equals":
            data = self.comma_equals_to_dict(data)
        self.new_data = {}
        self.timestamp = int(time.time())
        if self.key_level == 1:
            if "Time_Stamp" in data.keys():
                self.timestamp = data["Time_Stamp"]
                if "." not in self.timestamp:
                    if len(self.timestamp) >= 19:
                        self.timestamp = int(self.timestamp)
                        self.timestamp /= 1000000000
                    else:
                        self.timestamp = int(self.timestamp)
                else:
                    self.timestamp = float(self.timestamp)
        self.level_traverse("", data, 0)
        return self.new_data.copy()

    def comma_equals_to_dict(self, data):
        new_data = {}
        data = data.split(",")
        for row in data:
            if len(row) > 0:
                if "=" in row:
                    d = row.split("=")
                    if len(d) == 2:
                        k = d[0].strip()
                        v = d[1].strip()
                        if " " in k:
                            k = k.split(" ")[-1]
                        if " " in v:
                            v = v.split(" ")[0]
                        try:
                            v = float(v)
                            if v.is_integer():
                                v = int(v)
                        except Exception as e:
                            pass
                        new_data[k] = v
        return new_data

    def level_traverse(self, key, data, level):
        if isinstance(data, dict):
            level += 1
            for k, v in data.items():
                if key == "":
                    extended_key = k
                else:
                    extended_key = key+self.key_separator+k
                self.level_traverse(extended_key, v, level)
        else:
            if level == self.key_level:
                if key in self.key_map.keys():
                    topic = self.key_map[key]
                    senml_data = self.to_senml(topic, data, self.timestamp)
                    topic = self.pub_prefix + str(topic)
                    self.new_data[topic] = senml_data
                else:
                    topic = key
                    # not adding if key not present in config


    def to_senml(self, name, value, timestamp):
        meas = senml.SenMLMeasurement()
        meas.name = name
        if isinstance(value, str):
            try:
                value = float(value)
            except Exception:
                pass
        meas.value = value
        meas.time = timestamp
        doc = senml.SenMLDocument([meas], base=self.base)
        val = doc.to_json()
        val = json.dumps(val)
        return val


