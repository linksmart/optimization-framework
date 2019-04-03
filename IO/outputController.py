import json
import logging

import time

from senml import senml

from IO.ConfigParserUtils import ConfigParserUtils
from IO.MQTTClient import MQTTClient
from IO.redisDB import RedisDB
from IO.constants import Constants
import os
from random import randrange

from utils.messageLogger import MessageLogger

class OutputController:

    def __init__(self, id=None, output_config=None):
        self.logger = MessageLogger.get_logger(__file__, id)
        self.logger.info("Output Class started")
        self.output_config = output_config
        self.mqtt = {}
        self.client_id = "PROFESS"
        self.redisDB = RedisDB()
        self.mqtt_names = []
        self.mqtt_params = {}
        self.output_mqtt = {}
        self.id = id
        self.config_parser_utils = ConfigParserUtils()
        self.logger.debug("output_config: " + str(self.output_config) + " " + str(type(self.output_config)))
        if self.output_config is not None:
            self.extract_mqtt_params()
            self.init_mqtt()

    def extract_mqtt_params(self):
        self.logger.debug("Output config = " + str(self.output_config))
        for key, value in self.output_config.items():
            self.logger.debug("key " + str(key) + " value " + str(value))
            for key2, value2 in value.items():
                self.logger.debug("key2 " + str(key2) + " value2 " + str(value2))
                mqtt = self.config_parser_utils.get_mqtt(value2)
                unit, horizon_values = self.read_extra_values(value2)
                if mqtt is not None:
                    self.mqtt_params[key2] = mqtt.copy()
                    self.mqtt_params[key2]["unit"] = unit
                    self.mqtt_params[key2]["horizon_values"] = horizon_values
                    self.mqtt_names.append(key)
        self.logger.debug("params = " + str(self.mqtt_params))
        self.logger.debug("mqtt names = " + str(self.mqtt_names))

    def read_extra_values(self, value2):
        unit = None
        horizon_values = False
        if isinstance(value2, dict):
            if "unit" in value2.keys():
                unit = value2["unit"]
            if "horizon_values" in value2.keys():
                horizon_values = value2["horizon_values"]
        return unit, horizon_values

    def init_mqtt(self):
        ###Connection to the mqtt broker
        self.logger.debug("Starting init mqtt")
        self.redisDB.set("Error mqtt" + self.id, False)
        try:
            for key, value in self.mqtt_params.items():
                self.logger.debug("key " + str(key) + " value " + str(value))

                # self.output_mqtt[key2] = {"host":host, "topic":topic, "qos":qos}
                self.client_id = "client_publish" + str(randrange(100000)) + str(time.time()).replace(".", "")
                self.logger.debug("client " + str(self.client_id))
                self.logger.debug("host " + str(value["host"]))
                self.logger.debug("port " + str(value["mqtt.port"]))
                self.mqtt[key] = MQTTClient(str(value["host"]), value["mqtt.port"], self.client_id,
                                            username=value["username"], password=value["password"],
                                            ca_cert_path=value["ca_cert_path"], set_insecure=value["insecure"], id=self.id)
            self.logger.info("successfully subscribed")
        except Exception as e:
            self.logger.debug("Exception while starting mqtt")
            self.redisDB.set("Error mqtt" + self.id, True)
            self.logger.error(e)

    def publish_data(self, id, data, dT):
        self.logger.debug("output data : "+ json.dumps(data, indent=4))
        current_time = int(time.time())
        try:
            senml_data = self.senml_message_format(data, current_time, self.mqtt_params, dT)
            for key, value in senml_data.items():
                v = json.dumps(value)
                # self.logger.debug("key: "+str(key))
                # self.logger.debug("mqtt params: " + str(self.mqtt_params.keys()))
                if key in self.mqtt_params.keys():
                    value2 = self.mqtt_params[key]
                    topic = value2["topic"]
                    host = value2["host"]
                    qos = value2["qos"]
                    self.mqtt[key].sendResults(topic, v, qos)
        except Exception as e:
            self.logger.error("error in publish data ", e)
        self.save_to_redis(id, data, current_time)

    def Stop(self):
        self.stop_request = True

        try:
            for key, value in self.mqtt_params.items():
                self.logger.debug("key " + str(key) + " value " + str(value))
                self.mqtt[key].MQTTExit()
            self.logger.info("OutputController safe exit")
        except Exception as e:
            self.logger.error(e)

    def senml_message_format(self, data, current_time, params, dT):
        new_data = {}
        # self.logger.debug("data for senml "+str(data))
        u = None
        for key, value in data.items():
            flag = False
            time = current_time
            if key in params.keys():
                if params[key]["unit"] is not None:
                    u = params[key]["unit"]
                else:
                    u = "W"
                flag = params[key]["horizon_values"]
            meas_list = []
            for v in value:
                meas = senml.SenMLMeasurement()
                meas.name = key
                meas.time = time
                meas.value = v
                meas.unit = u
                meas_list.append(meas)
                time += dT
                if not flag:
                    break  # only want the first value
            if len(meas_list) > 0:
                doc = senml.SenMLDocument(meas_list)
                new_data[key] = doc.to_json()
        # self.logger.debug("Topic MQTT Senml message: "+str(new_data))
        return new_data

    def save_to_redis(self, id, data, time):
        try:
            part_key = "o:" + id + ":"
            output_keys = self.redisDB.get_keys_for_pattern(part_key+"*")
            if output_keys is not None:
                for key in output_keys:
                    self.redisDB.remove(key)
            for key, value in data.items():
                index = 0
                for v in value:
                    k = part_key + key + ":" + str(index)
                    self.redisDB.set(k, json.dumps({str(time): v}))
                    index += 1
        except Exception as e:
            self.logger.error("error adding to redis " + str(e))
