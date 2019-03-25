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

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class OutputController:

    def __init__(self, id=None, output_config=None):
        logger.info("Output Class started")
        self.output_config = output_config
        self.mqtt = {}
        self.client_id = "PROFESS"
        self.redisDB = RedisDB()
        self.mqtt_names = []
        self.mqtt_params = {}
        self.output_mqtt = {}
        self.id = id
        self.config_parser_utils = ConfigParserUtils()
        logger.debug("output_config: " + str(self.output_config) + " " + str(type(self.output_config)))
        if self.output_config is not None:
            self.extract_mqtt_params()
            self.init_mqtt()

    def extract_mqtt_params(self):
        logger.debug("Output config = " + str(self.output_config))
        for key, value in self.output_config.items():
            logger.debug("key " + str(key) + " value " + str(value))
            for key2, value2 in value.items():
                logger.debug("key2 " + str(key2) + " value2 " + str(value2))
                mqtt = self.config_parser_utils.get_mqtt(value2)
                unit, horizon_values = self.read_extra_values(value2)
                if mqtt is not None:
                    self.mqtt_params[key2] = mqtt.copy()
                    self.mqtt_params[key2]["unit"] = unit
                    self.mqtt_params[key2]["horizon_values"] = horizon_values
                    self.mqtt_names.append(key)
        logger.debug("params = " + str(self.mqtt_params))
        logger.debug("mqtt names = " + str(self.mqtt_names))

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
        logger.debug("Starting init mqtt")
        self.redisDB.set("Error mqtt" + self.id, False)
        try:
            for key, value in self.mqtt_params.items():
                logger.debug("key " + str(key) + " value " + str(value))

                # self.output_mqtt[key2] = {"host":host, "topic":topic, "qos":qos}
                self.client_id = "client_publish" + str(randrange(100000)) + str(time.time()).replace(".", "")
                logger.debug("client " + str(self.client_id))
                logger.debug("host " + str(value["host"]))
                logger.debug("port " + str(value["mqtt.port"]))
                self.mqtt[key] = MQTTClient(str(value["host"]), value["mqtt.port"], self.client_id,
                                            username=value["username"],
                                            password=value["password"],
                                            ca_cert_path=value["ca_cert_path"],
                                            set_insecure=value["insecure"])
            logger.info("successfully subscribed")
        except Exception as e:
            logger.debug("Exception while starting mqtt")
            self.redisDB.set("Error mqtt" + self.id, True)
            logger.error(e)

    def publish_data(self, id, data, dT):
        # logger.debug("data "+str(data))
        current_time = int(time.time())
        try:
            senml_data = self.senml_message_format(data, current_time, self.mqtt_params, dT)
            for key, value in senml_data.items():
                v = json.dumps(value)
                # logger.debug("key: "+str(key))
                # logger.debug("mqtt params: " + str(self.mqtt_params.keys()))
                if key in self.mqtt_params.keys():
                    value2 = self.mqtt_params[key]
                    topic = value2["topic"]
                    host = value2["host"]
                    qos = value2["qos"]
                    self.mqtt[key].sendResults(topic, v, qos)
        except Exception as e:
            logger.error("error in publish data ", e)
        self.save_to_redis(id, data, current_time)

    def Stop(self):
        self.stop_request = True

        try:
            for key, value in self.mqtt_params.items():
                logger.debug("key " + str(key) + " value " + str(value))
                self.mqtt[key].MQTTExit()
            logger.info("OutputController safe exit")
        except Exception as e:
            logger.error(e)

    def senml_message_format(self, data, current_time, params, dT):
        new_data = {}
        # logger.debug("data for senml "+str(data))
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
            first = False
            if len(value) > 1:
                first = True
            for v in value:
                if first:
                    first = False
                    if not flag:
                        time += dT
                        continue
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
        # logger.debug("Topic MQTT Senml message: "+str(new_data))
        return new_data

    def save_to_redis(self, id, data, time):
        try:
            part_key = "o:" + id + ":"
            for key, value in data.items():
                index = 0
                for v in value:
                    k = part_key + key + ":" + str(index)
                    self.redisDB.set(k, json.dumps({str(time): v}))
                    index += 1
        except Exception as e:
            logger.error("error adding to redis " + str(e))
