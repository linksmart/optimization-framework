"""
Created on Aug 03 14:22 2018

@author: nishit
"""
import logging

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class InputConfigParser:

    def __init__(self, input_config):
        self.input_config = input_config
        self.mqtt_params = {}
        self.extract_mqtt_params()

    def extract_mqtt_params(self):
        for key, value in self.input_config.items():
            for key2, value2 in value.items():
                host = None
                topic = None
                qos = 0
                if isinstance(value2, dict) and "mqtt" in value2.keys():
                    if "host" in value2["mqtt"].keys():
                        host = value2["mqtt"]["host"]
                    if "topic" in value2["mqtt"].keys():
                        topic = value2["mqtt"]["topic"]
                    if "qos" in value2["mqtt"].keys():
                        qos = value2["mqtt"]["qos"]
                    if host is not None and topic is not None:
                        self.mqtt_params[key2] = {"host":host,
                                                 "topic":topic,
                                                 "qos":qos}
        logger.info("params = "+str(self.mqtt_params))

    def get_params(self, topic):
        return self.mqtt_params[topic]

    def get_optimization_values(self):
        data = {}
        for k, v in self.input_config.items():
            if isinstance(v, dict):
                for k1, v1 in v.items():
                    if k1 == "meta":
                        for k2, v2 in v1.items():
                            v2 = float(v2)
                            if v2.is_integer():
                                v2 = int(v2)
                            if k == "ESS":
                                data[k2] = {0: v2}
                            else:
                                data[k2] = {None: v2}
                    else:
                        if isinstance(v1, dict):
                            for k2, v2 in v1.items():
                                if k1 == "SoC_Value" and k2 == "value_percent":
                                    v2 = float(v2)
                                    if v2.is_integer():
                                        v2 = int(v2)
                                    data["ESS_SoC_Value"] = {0: float(v2 / 100)}
        return data

    def get_forecast_flag(self, topic, default):
        if topic in self.input_config.keys():
            return bool(self.input_config[topic]["Internal_Forecast"])
        else:
            return default