"""
Created on Jul 09 14:02 2019

@author: nishit
"""
from optimization.baseEventDataReceiver import BaseEventDataReceiver


class GenericEventDataReceiver(BaseEventDataReceiver):

    def preprocess_data(self, base, name, value, unit):
        if "charger" in base:
            s = name.split("/")
            data = {}
            if len(s) == 2:
                data["Hosted_EV"] = s[0]
                data[s[1]] = value
            else:
                data[s[-1]] = value
            base = base.split("/")[-1]
            return {base: data}
        return {}