"""
Created on Jan 28 12:26 2020

@author: nishit
"""
import json

import time
from senml import senml

from IO.dataReceiver import DataReceiver


class Status(DataReceiver):
    def __init__(self, internal, topic_params, config):
        super().__init__(internal, topic_params, config)

    def on_msg_received(self, payload):
        senml_data = json.loads(payload)
        formated_data = self.add_formated_data(senml_data)
        self.data.update(formated_data)
        self.data_update = True

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
            doc.measurements = sorted(doc.measurements, key=lambda x: x.time)
            if len(doc.measurements) > 0:
                for meas in doc.measurements:
                    n = meas.name
                    t = meas.time
                    v = meas.value
                    data[n] = {"last_time":t, "freq":v}
            return data
        return {}

    def remove_entries(self, instance_ids):
        for id in instance_ids:
            if id in self.data.keys():
                self.data.pop(id)

    def set_to_current_time(self, instance_ids):
        current_time = int(time.time())
        for id in instance_ids:
            if id in self.data.keys():
                self.data[id]["last_time"] = current_time