"""
Created on Aug 03 14:22 2018

@author: nishit
"""
import logging

from IO.constants import Constants

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class InputConfigParser:

    def __init__(self, input_config_file, input_config_mqtt):
        self.input_config_file = input_config_file
        self.input_config_mqtt = input_config_mqtt
        self.mqtt_params = {}
        self.generic_names = []
        self.generic_file_names = []
        self.defined_prediction_names = ["P_Load", "P_Load_R", "P_Load_S", "P_Load_T", "Q_Load_R", "Q_Load_S", "Q_Load_T"]
        self.defined_non_prediction_names = ["P_PV"]
        self.defined_external_names = ["SoC_Value"]
        self.defined_receivers = []
        self.defined_receivers.append(self.defined_prediction_names)
        self.defined_receivers.append(self.defined_non_prediction_names)
        self.defined_receivers.append(self.defined_external_names)
        self.prediction_names = []
        self.non_prediction_names = []
        self.external_names = []

        self.extract_mqtt_params()
        self.optimization_params = self.extract_optimization_values()
        logger.debug("optimization_params: "+str(self.optimization_params))
        logger.info("generic names = "+str(self.generic_names))


    def get_mqtt(self, value2):
        if isinstance(value2, dict) and Constants.mqtt in value2.keys():
            host = None
            topic = None
            qos = 0
            if "host" in value2[Constants.mqtt].keys():
                host = value2[Constants.mqtt]["host"]
            if "topic" in value2[Constants.mqtt].keys():
                topic = value2[Constants.mqtt]["topic"]
            if "qos" in value2[Constants.mqtt].keys():
                qos = value2[Constants.mqtt]["qos"]
            if host is not None and topic is not None:
                return {"host": host, "topic": topic, "qos": qos}
            else:
                return None
        else:
            return None

    def extract_mqtt_params(self):
        for key, value in self.input_config_mqtt.items():
            if key == "generic":
                for value1 in value:
                    if "name" in value1.keys():
                        name = value1["name"]
                        if "generic_name" in value1.keys():
                            value2 = value1["generic_name"]
                            mqtt = self.get_mqtt(value2)
                            if mqtt is not None:
                                self.mqtt_params[name] = mqtt.copy()
                                self.generic_names.append(name)
            else:
                for key2, value2 in value.items():
                    mqtt = self.get_mqtt(value2)
                    if mqtt is not None:
                        self.mqtt_params[key2] = mqtt.copy()
                        self.add_name_to_list(key2)
        logger.info("params = "+str(self.mqtt_params))

    def add_name_to_list(self, key):
        if key in self.defined_prediction_names:
            self.prediction_names.append(key)
        elif key in self.defined_non_prediction_names:
            self.non_prediction_names.append(key)
        elif key in self.defined_external_names:
            self.external_names.append(key)
        else:
            self.generic_names.append(key)

    def get_params(self, topic):
        return self.mqtt_params[topic]

    def get_optimization_values(self):
        return self.optimization_params

    def extract_optimization_values(self):
        data = {}
        for input_config in [self.input_config_file, self.input_config_mqtt]:
            for k, v in input_config.items():
                if isinstance(v, dict):
                    logger.debug("k: "+str(k)+" v: "+str(v))
                    for k1, v1 in v.items():
                        #logger.debug("k1: " + str(k1) + " v1: " + str(v1))
                        if k1 == Constants.meta:
                            for k2, v2 in v1.items():
                                logger.debug("k2: " + str(k2) + " v2: " + str(v2))
                                v2 = float(v2)
                                if v2.is_integer():
                                    v2 = int(v2)
                                if k == Constants.ESS:
                                    data[k2] = {None: v2}
                                else:
                                    data[k2] = {None: v2}
                        elif k1 == Constants.SoC_Value and isinstance(v1, float):
                            logger.debug("Constants.SoC_Value: "+str(v1))
                            data["SoC_Value"] = {None: float(v1)}
                        elif isinstance(v1, list):
                            self.add_name_to_list(k1)
                if k == "generic" and input_config == self.input_config_file:
                    for val in v:
                        for k1, v1 in val.items():
                            if k1 == "name":
                                self.generic_names.append(v1)
        return data

    def get_forecast_flag(self, topic):
        if topic in self.mqtt_params:
            return True
        else:
            return False

    def get_generic_data_names(self):
        return self.generic_names

    def get_prediction_names(self):
        return self.prediction_names

    def get_non_prediction_names(self):
        return self.non_prediction_names

    def get_external_names(self):
        return self.external_names
