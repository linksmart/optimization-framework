"""
Created on Okt 19 11:54 2018

@author: nishit
"""
import json
import logging

import time
from senml import senml

from IO.RecPub import RecPub

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class Connector(RecPub):

    def __init__(self, receiver_params, config):
        super().__init__(receiver_params, None, config)
        self.pub_prefix = config.get("IO","pub.topic.prefix")
        self.key_level = int(config.get("KEY_META","level"))
        self.key_separator = config.get("KEY_META","key.separator")
        self.key_map = dict(config.items("KEYS"))

    def data_formater(self, data):
        data = json.loads(data)
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
        doc = senml.SenMLDocument([meas])
        val = doc.to_json()
        val = json.dumps(val)
        return val


