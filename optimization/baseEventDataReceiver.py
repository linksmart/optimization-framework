"""
Created on Aug 13 11:03 2018

@author: nishit
"""
import json
from abc import ABC, abstractmethod

from senml import senml

from IO.dataReceiver import DataReceiver
from IO.redisDB import RedisDB
from utils_intern.messageLogger import MessageLogger


class BaseEventDataReceiver(DataReceiver, ABC):

    def __init__(self, internal, topic_params, config, generic_name, id, event_callback):
        redisDB = RedisDB()
        self.logger = MessageLogger.get_logger(__name__, id)
        self.generic_name = generic_name
        self.event_callback = event_callback
        try:
            super().__init__(internal, topic_params, config, id=id)
        except Exception as e:
            redisDB.set("Error mqtt" + self.id, True)
            self.logger.error(e)

    def on_msg_received(self, payload):
        try:
            senml_data = json.loads(payload)
            formated_data = self.add_formated_data(senml_data)
            self.data.update(formated_data)
            self.event_callback(formated_data)
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
                    if not u:
                        u = bu
                    if not n:
                        n = self.generic_name
                    try:
                        processed_value = self.preprocess_data(bn, n, v, u)
                        raw_data.append([t,processed_value])
                    except Exception as e:
                        self.logger.error("error " + str(e) + "  n = " + str(n))
            data[self.generic_name] = raw_data
            return data
        return {}

    @abstractmethod
    def preprocess_data(self, base, name, value, unit):
        return value
