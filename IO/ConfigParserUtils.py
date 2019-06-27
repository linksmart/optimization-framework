"""
Created on Feb 12 17:50 2019

@author: nishit
"""
import logging
import os

from IO.constants import Constants

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class ConfigParserUtils:

    def get_mqtt(self, value):
        if isinstance(value, dict) and Constants.mqtt in value.keys():
            host = None
            topic = None
            qos = 0
            port = 1883
            username = None
            password = None
            ca_cert_path = None
            insecure = False
            detachable = False
            if "host" in value[Constants.mqtt].keys():
                host = value[Constants.mqtt]["host"]
            if "topic" in value[Constants.mqtt].keys():
                topic = value[Constants.mqtt]["topic"]
            if "qos" in value[Constants.mqtt].keys():
                qos = value[Constants.mqtt]["qos"]
            if "port" in value[Constants.mqtt].keys():
                port = value[Constants.mqtt]["port"]
            if "username" in value[Constants.mqtt].keys():
                username = value[Constants.mqtt]["username"]
            if "password" in value[Constants.mqtt].keys():
                password = value[Constants.mqtt]["password"]
            if "ca_cert_path" in value[Constants.mqtt].keys():
                ca_cert_path = value[Constants.mqtt]["ca_cert_path"]
                ca_cert_path = os.path.join("/usr/src/app", ca_cert_path)
            if "insecure" in value[Constants.mqtt].keys():
                insecure = value[Constants.mqtt]["insecure"]
            if "detachable" in value[Constants.mqtt].keys():
                detachable = value[Constants.mqtt]["detachable"]
            if host is not None and topic is not None:
                return {"host": host, "topic": topic, "qos": qos, "mqtt.port": port, "username":username,
                        "password":password, "ca_cert_path":ca_cert_path, "insecure":insecure, "detachable":detachable}
            else:
                return None
        else:
            return None