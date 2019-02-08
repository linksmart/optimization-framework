import json
import logging

import time

from senml import senml

from IO.MQTTClient import MQTTClient
from IO.redisDB import RedisDB

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class OutputController:

    def __init__(self, output_config=None, id=None):
        logger.info("Output Class started")
        self.output_config=output_config
        self.mqtt={}
        self.client_id = "PROFESS"
        self.redisDB = RedisDB()
        self.output_mqtt = {}
        self.id=id

        if output_config is not None:
            self.init_mqtt()

    def init_mqtt(self):
        ###Connection to the mqtt broker
        self.redisDB.set("Error mqtt"+self.id, False)
        try:
            for key, value in self.output_config.items():
                for key2, value2 in value.items():
                    if (value2["mqtt"]["host"] or value2["mqtt"]["host"].isspace()):
                        host=value2["mqtt"]["host"]
                        topic = value2["mqtt"]["topic"]
                        qos = value2["mqtt"]["qos"]
                        if "qos" in value2["mqtt"]:
                            qos = value2["mqtt"]["qos"]
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
        current_time = int(time.time())
        senml_data = self.senml_message_format(data, current_time)
        try:
            for key, value in senml_data.items():
                v = json.dumps(value)
                if key in self.output_mqtt.keys():
                    value2 = self.output_mqtt[key]
                    topic = value2["topic"]
                    host = value2["host"]
                    qos = value2["qos"]
                    self.mqtt[str(host)].sendResults(topic, v)
        except Exception as e:
            logger.error(e)
        self.save(id, data, current_time)


    def senml_message_format(self, data, time):
        new_data = {}
        u = "W"
        for key, value in data.items():
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