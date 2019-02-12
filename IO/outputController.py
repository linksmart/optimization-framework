import json
import logging

import time

from senml import senml

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
        self.output_config=output_config
        self.mqtt={}
        self.client_id = "PROFESS"
        self.redisDB = RedisDB()
        self.mqtt_names= []
        self.mqtt_params = {}
        self.output_mqtt = {}
        self.id=id

        logger.debug("output_config: "+str(self.output_config)+" "+str(type(self.output_config)))
        if self.output_config is not None:
            self.extract_mqtt_params()
            self.init_mqtt()




    def get_mqtt(self, value2):
        if isinstance(value2, dict) and Constants.mqtt in value2.keys():
            host = None
            topic = None
            qos = 0
            port = None
            username = None
            password = None
            ca_cert_path = None
            insecure = False
            unit = None
            logger.debug("unit in constants: "+str(value2[Constants.mqtt].keys()))
            if "host" in value2[Constants.mqtt].keys():
                host = value2[Constants.mqtt]["host"]
            if "topic" in value2[Constants.mqtt].keys():
                topic = value2[Constants.mqtt]["topic"]
            if "qos" in value2[Constants.mqtt].keys():
                qos = value2[Constants.mqtt]["qos"]
            if "port" in value2[Constants.mqtt].keys():
                port = value2[Constants.mqtt]["port"]
            if "username" in value2[Constants.mqtt].keys():
                username = value2[Constants.mqtt]["username"]
            if "password" in value2[Constants.mqtt].keys():
                password = value2[Constants.mqtt]["password"]
            if "ca_cert_path" in value2[Constants.mqtt].keys():
                ca_cert_path = value2[Constants.mqtt]["ca_cert_path"]
                ca_cert_path = os.path.join("/usr/src/app", ca_cert_path)
            if "insecure" in value2[Constants.mqtt].keys():
                insecure = value2[Constants.mqtt]["insecure"]
            if "unit" in value2.keys():
                unit = value2[Constants.unit]
            if host is not None and topic is not None:
                if port is not None:
                    return {"host": host, "topic": topic, "qos": qos, "mqtt.port": port, "username":username,
                        "password":password, "ca_cert_path":ca_cert_path, "insecure":insecure, "unit":unit}
                else:
                    return {"host": host, "topic": topic, "qos": qos, "mqtt.port": "1883", "username": username,
                            "password": password, "ca_cert_path": ca_cert_path, "insecure": insecure, "unit": unit}

            else:
                return None
            logger.debug("Finish with get mqtt")
        else:
            return None

    def extract_mqtt_params(self):
        logger.debug("Output config = " + str(self.output_config))
        for key, value in self.output_config.items():
            logger.debug("key " + str(key) + " value " + str(value))
            for key2, value2 in value.items():
                logger.debug("key2 " + str(key2) + " value2 " + str(value2))
                mqtt = self.get_mqtt(value2)
                if mqtt is not None:
                    self.mqtt_params[key2] = mqtt.copy()
                    self.mqtt_names.append(key)
        logger.debug("params = "+str(self.mqtt_params))
        logger.debug("mqtt names = " + str(self.mqtt_names))




    def init_mqtt(self):
        ###Connection to the mqtt broker
        logger.debug("Starting init mqtt")
        self.redisDB.set("Error mqtt"+self.id, False)
        try:
            for key, value in self.mqtt_params.items():
                logger.debug("key " + str(key) + " value " + str(value))

                #self.output_mqtt[key2] = {"host":host, "topic":topic, "qos":qos}
                self.client_id = "client_publish" + str(randrange(100000)) + str(time.time()).replace(".", "")
                logger.debug("client "+str(self.client_id))
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

    def init_mqtt_1(self):
        ###Connection to the mqtt broker
        self.redisDB.set("Error mqtt"+self.id, False)
        try:
            for key, value in self.output_config.items():
                logger.debug("key " + str(key) + " value " + str(value))
                for key2, value2 in value.items():
                    logger.debug("key2 "+str(key2)+" value2 "+str(value2))
                    if (value2["mqtt"]["host"] or value2["mqtt"]["host"].isspace()):
                        host=value2["mqtt"]["host"]
                        topic = value2["mqtt"]["topic"]
                        qos = value2["mqtt"]["qos"]
                        if "qos" in value2["mqtt"]:
                            qos = value2["mqtt"]["qos"]
                        if "unit" in value2:
                            logger.debug("unit "+str(value2["unit"]))
                        self.output_mqtt[key2] = {"host":host, "topic":topic, "qos":qos}
                        if bool(self.mqtt):
                            if host in self.mqtt:
                                logger.debug("Already connected to the host "+host)
                            else:
                                logger.debug("Creating mqtt client with the host: " + str(host))
                                self.mqtt[str(host)] = MQTTClient(str(host), 1883, self.client_id)
                        else:
                            logger.debug("Creating mqtt client with the host: " + str(host))
                            self.mqtt[str(host)] = MQTTClient(str(host), 1883, self.client_id)
                    logger.debug("Self.mqtt: " + str(self.mqtt))
        except Exception as e:
            logger.debug("Exception while starting mqtt")
            self.redisDB.set("Error mqtt" + self.id, True)
            logger.error(e)

    def publishController(self, id, data):
        #logger.debug("data "+str(data))
        current_time = int(time.time())
        senml_data = self.senml_message_format(data, current_time, self.mqtt_params)
        try:
            for key, value in senml_data.items():
                v = json.dumps(value)
                #logger.debug("key: "+str(key))
                #logger.debug("mqtt params: " + str(self.mqtt_params.keys()))
                if key in self.mqtt_params.keys():
                    value2 = self.mqtt_params[key]
                    topic = value2["topic"]
                    host = value2["host"]
                    qos = value2["qos"]
                    self.mqtt[key].sendResults(topic, v)
        except Exception as e:
            logger.error(e)
        self.save(id, data, current_time)

    def Stop(self):
        self.stop_request = True

        try:
            for key, value in self.mqtt_params.items():
                logger.debug("key " + str(key) + " value " + str(value))
                self.mqtt[key].MQTTExit()
            logger.info("OutputController safe exit")
        except Exception as e:
            logger.error(e)

    def senml_message_format(self, data, time, params):
        new_data = {}

        #logger.debug("data for senml "+str(data))
        u=None
        for key, value in data.items():
            if key in params.keys():
                if params[key]["unit"] is not None:
                    u=params[key]["unit"]
                else:
                    u="W"
            meas_list = []
            first = False
            if len(value) > 1:
                first = True
            for v in value:
                if first:
                    first = False
                    continue
                meas = senml.SenMLMeasurement()
                meas.name = key
                meas.time = time
                meas.value = v
                meas.unit = u
                meas_list.append(meas)
                break  # only want the first value
            if len(meas_list) > 0:
                doc = senml.SenMLDocument(meas_list)
                new_data[key] = doc.to_json()
        #logger.debug("Topic MQTT Senml message: "+str(new_data))
        return new_data

    def makeFile(self):
        return 0

    def save(self, id, data, time):
        try:
            part_key = "o:" + id + ":"
            for key, value in data.items():
                index = 0
                for v in value:
                    k = part_key + key + ":" + str(index)
                    self.redisDB.set(k, json.dumps({str(time):v}))
                    index += 1
        except Exception as e:
            logger.error("error adding to redis " + str(e))