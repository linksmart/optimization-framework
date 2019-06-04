"""
Created on Mai 28 14:22 2019

@author: nishit
"""
from optimization.baseDataReceiver import BaseDataReceiver


class ChargerDataReceiver(BaseDataReceiver):

    def __init__(self, internal, topic_params, config, generic_name, id, buffer, dT):
        super().__init__(internal, topic_params, config, generic_name, id, buffer, dT, True)

    def unit_value_change(self, value, unit):
        return value

    def preprocess_data(self, base, name, value):
        if "charger" in base:
            s = name.split("/")
            if len(s) > 1:
                data = {"Hosted_Car": s[0]}
                data[s[1]] = value
                return {base: data}
        return {}