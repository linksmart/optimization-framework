"""
Created on Aug 10 12:11 2018

@author: nishit
"""
import json
import logging
from senml import senml

from IO.dataReceiver import DataReceiver

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class GenericDataReceiver(DataReceiver):

    def __init__(self, internal, topic_params, config, generic_name):
        super().__init__(internal, topic_params, config)
        self.generic_name = generic_name

    def on_msg_received(self, payload):
        senml_data = json.loads(payload)
        formated_data = self.add_formated_data(senml_data)
        self.data.update(formated_data)
        self.data_update = True
        logger.debug("generic data received")

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
            index = {}
            for meas in doc.measurements:
                n = meas.name
                u = meas.unit
                v = meas.value
                if not u:
                    u = bu
                if bn and n and bn != n:
                    n = bn + n
                if not n:
                    n = bn
                if n == self.generic_name:
                    # change value as per unit requirements
                    if n not in index.keys():
                        index[n] = 0
                    if n not in data.keys():
                        data[n] = {}
                    data[n][index[n]] = v
                    index[n] += 1
            return data
        return {}
