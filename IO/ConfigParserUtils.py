"""
Created on Feb 12 17:50 2019

@author: nishit
"""
import os

from utils_intern.constants import Constants

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()


class ConfigParserUtils:

    @staticmethod
    def get_mqtt(mqtt_dict):
        if isinstance(mqtt_dict, dict):
            if Constants.mqtt in mqtt_dict.keys():
                mqtt_dict = mqtt_dict[Constants.mqtt]
            host = ConfigParserUtils.read_value("host", mqtt_dict, None)
            topic = ConfigParserUtils.read_value("topic", mqtt_dict, None)
            qos = ConfigParserUtils.read_value("qos", mqtt_dict, 0)
            port = ConfigParserUtils.read_value("port", mqtt_dict, 1883)
            username = ConfigParserUtils.read_value("username", mqtt_dict, None)
            password = ConfigParserUtils.read_value("password", mqtt_dict, None)
            ca_cert_path = ConfigParserUtils.read_value("ca_cert_path", mqtt_dict, None)
            insecure = ConfigParserUtils.read_value("insecure", mqtt_dict, False)
            detachable = ConfigParserUtils.read_value("detachable", mqtt_dict, False)
            reuseable = ConfigParserUtils.read_value("reuseable", mqtt_dict, False)
            option = ConfigParserUtils.read_value("option", mqtt_dict, None)
            if ca_cert_path:
                ca_cert_path = os.path.join("/usr/src/app", ca_cert_path)

            if host is not None and topic is not None:
                return {"host": host, "topic": topic, "qos": qos, "mqtt.port": port, "username": username,
                        "password": password, "ca_cert_path": ca_cert_path, "insecure": insecure,
                        "detachable": detachable, "reuseable": reuseable, "option": option}
            else:
                return None
        else:
            return None

    @staticmethod
    def read_value(name, dict, default):
        if name in dict.keys():
            return dict[name]
        else:
            return default

    @staticmethod
    def extract_mqtt_params_output(output_config, filter_key=None, include=False):
        mqtt_params = {}
        if output_config:
            logger.debug("Output config = " + str(output_config))
            for key, value in output_config.items():
                logger.debug("key " + str(key) + " value " + str(value))
                if filter_key is None or (filter_key == key and include) or (filter_key != key and not include):
                    for key2, value2 in value.items():
                        logger.debug("key2 " + str(key2) + " value2 " + str(value2))
                        mqtt = ConfigParserUtils.get_mqtt(value2)
                        unit, horizon_values, base_name = ConfigParserUtils.read_extra_values_output(value2)
                        if mqtt is not None:
                            mqtt_params[key2] = mqtt.copy()
                            mqtt_params[key2]["unit"] = unit
                            mqtt_params[key2]["horizon_values"] = horizon_values
                            mqtt_params[key2]["base_name"] = base_name
            logger.debug("params = " + str(mqtt_params))
        return mqtt_params

    @staticmethod
    def read_extra_values_output(value2):
        unit = None
        horizon_values = False
        base_name = False
        if isinstance(value2, dict):
            if "unit" in value2.keys():
                unit = value2["unit"]
            if "horizon_values" in value2.keys():
                horizon_values = value2["horizon_values"]
            if "base_name" in value2.keys():
                base_name = value2["base_name"]
            else:
                base_name = ""
        return unit, horizon_values, base_name

    @staticmethod
    def extract_host_params(host, port, topic_params, config, section):
        qos = 1
        topic = None
        host_params = {}
        host_params["username"] = config.get("IO", "mqtt.username", fallback=None)
        host_params["password"] = config.get("IO", "mqtt.password", fallback=None)
        host_params["ca_cert_path"] = config.get("IO", "mqtt.ca.cert.path", fallback=None)
        host_params["insecure_flag"] = bool(config.get("IO", "mqtt.insecure.flag", fallback=False))
        if section is not None:
            if "mqtt.username" in dict(config.items(section)):
                host_params["username"] = config.get(section, "mqtt.username", fallback=None)
            if "mqtt.password" in dict(config.items(section)):
                host_params["password"] = config.get(section, "mqtt.password", fallback=None)
            if "mqtt.ca.cert.path" in dict(config.items(section)):
                host_params["ca_cert_path"] = config.get(section, "mqtt.ca.cert.path", fallback=None)
            if "mqtt.insecure.flag" in dict(config.items(section)):
                host_params["insecure_flag"] = bool(config.get(section, "mqtt.insecure.flag", fallback=False))
        if topic_params:
            topic = topic_params["topic"]
            if "host" in topic_params.keys():
                host = topic_params["host"]
            if "qos" in topic_params.keys():
                qos = topic_params["qos"]
            if "mqtt.port" in topic_params.keys():
                port = topic_params["mqtt.port"]
            if "username" in topic_params.keys():
                host_params["username"] = topic_params["username"]
            if "password" in topic_params.keys():
                host_params["password"] = topic_params["password"]
            if "ca_cert_path" in topic_params.keys():
                host_params["ca_cert_path"] = topic_params["ca_cert_path"]
            if "insecure" in topic_params.keys():
                host_params["insecure_flag"] = topic_params["insecure"]
        return host, host_params, qos, topic, port