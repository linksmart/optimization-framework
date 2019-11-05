"""
Created on Feb 12 17:50 2019

@author: nishit
"""
import os

from utils_intern.constants import Constants

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class ConfigParserUtils:

    def get_mqtt(self, value):
        if isinstance(value, dict) and Constants.mqtt in value.keys():
            mqtt_dict = value[Constants.mqtt]
            host = self.read_value("host", mqtt_dict, None)
            topic = self.read_value("topic", mqtt_dict, None)
            qos = self.read_value("qos", mqtt_dict, 0)
            port = self.read_value("port", mqtt_dict, 1883)
            username = self.read_value("username", mqtt_dict, None)
            password = self.read_value("password", mqtt_dict, None)
            ca_cert_path = self.read_value("ca_cert_path", mqtt_dict, None)
            insecure = self.read_value("insecure", mqtt_dict, False)
            detachable = self.read_value("detachable", mqtt_dict, False)
            reuseable = self.read_value("reuseable", mqtt_dict, False)
            if ca_cert_path:
                ca_cert_path = os.path.join("/usr/src/app", ca_cert_path)

            if host is not None and topic is not None:
                return {"host": host, "topic": topic, "qos": qos, "mqtt.port": port, "username": username,
                        "password": password, "ca_cert_path": ca_cert_path, "insecure": insecure,
                        "detachable": detachable, "reuseable": reuseable}
            else:
                return None
        else:
            return None

    def read_value(self, name, dict, default):
        if name in dict.keys():
            return dict[name]
        else:
            return default
