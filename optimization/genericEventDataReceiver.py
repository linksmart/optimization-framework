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
            event = None
            charger_name = None
            base_name = base.split("/")
            if len(base_name) == 2:
                charger_name = base_name[1]
            if len(s) == 2:
                data["Hosted_EV"] = s[0]
                data[s[1]] = value
                event = s[1]
            else:
                data[s[-1]] = value
                event = s[-1]
            gen_name = None
            if event is not None and charger_name is not None:
                gen_name = charger_name + "/" + event
            if gen_name == self.name:
                base = base.split("/")[-1]
                return {base: data}
            else:
                # self.logger.debug("other charger data, so ignore "+str(gen_name)+ " - "+str(self.generic_name))
                return None
        return None