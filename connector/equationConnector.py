"""
Created on Sep 19 15:32 2019

@author: nishit
"""
import json
import threading

from senml import senml

from IO.summationPub import SummationPub
from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class EquationConnector(SummationPub):

    def __init__(self, meta_eq, config):
        self.stopRequest = threading.Event()
        self.meta_eq = meta_eq
        self.variables = self.meta_eq["variables"]
        super().__init__(meta_eq["topics"], config)
        self.sum_data_thread = threading.Thread(target=self.sum_data)
        self.sum_data_thread.start()
        logger.debug("###### start equation")

    def data_formater(self, data):
        json_data = json.loads(data)
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
        new_data = {}
        if doc:
            base_data = doc.base
            bn = None
            if base_data:
                bn = base_data.name
                bn = bn.replace("/","")
            if len(doc.measurements) > 0:
                for meas in doc.measurements:
                    n = meas.name
                    u = meas.unit
                    v = meas.value
                    t = meas.time
                    new_data[bn+"."+n] = v
        return new_data

    def sum_data(self):
        while True and not self.stopRequest.is_set():
            logger.debug("#### waiting for all data")
            data = self.rec.get_data(require_updated=0)
            logger.debug("################# data = "+str(data))
            logger.debug("########### variables = "+str(self.variables))
            all_vars_available = True
            for var in self.variables:
                if var not in data.keys():
                    all_vars_available = False
                    break
            if all_vars_available:
                self.rec.clear_data()
                result = data[self.variables[0]]
                for i in range(1, len(self.variables)):
                    if self.meta_eq["ops"][i-1] == "+":
                        result += data[self.variables[i]]
                    else:
                        result -= data[self.variables[i]]
                senml_data = self.to_senml(self.meta_eq["name"], result, self.rec.last_time)
                d = {"topic": self.meta_eq["pub_topic"], "data": senml_data}
                self.q.put(d)

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
