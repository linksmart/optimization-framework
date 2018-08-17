import json
import logging

import time

from senml import senml

from IO.MQTTClient import MQTTClient
from IO.redisDB import RedisDB

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class OutputController:

    def __init__(self, output_config=None):
        logger.info("Output Class started")
        self.output_config=output_config
        self.mqtt={}
        self.client_id = "PROFESS"
        self.redisDB = RedisDB()
        self.output_mqtt = {}

        if output_config is not None:
            self.init_mqtt()

    def init_mqtt(self):
        ###Connection to the mqtt broker
        try:
            for key, value in self.output_config.items():
                for key2, value2 in value.items():
                    if (value2["mqtt"]["host"] or value2["mqtt"]["host"].isspace()):
                        host=value2["mqtt"]["host"]
                        topic = value2["mqtt"]["topic"]
                        qos = 0
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
            logger.error(e)

    def publishController(self, id, data):
        data = self.senml_message_format(data)
        try:
            for key, value in data.items():
                v = json.dumps(data[key])
                self.save(id, key, v)
                if key in self.output_mqtt.keys():
                    value2 = self.output_mqtt[key]
                    topic = value2["topic"]
                    host = value2["host"]
                    qos = value2["qos"]
                    self.mqtt[str(host)].sendResults(topic, v)
        except Exception as e:
            logger.error(e)


    def senml_message_format(self, data):
        new_data = {}
        current_time = int(time.time())
        u = "W"
        for key, value in data.items():
            topic_data = {}
            for v in value[0]:
                if v is not 0:
                    meas = senml.SenMLMeasurement()
                    meas.name = key
                    meas.time = current_time
                    meas.value = v
                    meas.unit = u
                    doc = senml.SenMLDocument([meas])
                    topic_data["e"] = doc.to_json()
            new_data[key] = topic_data.copy()
        return new_data

    def makeFile(self):
        return 0

    def save(self, id, topic, value):
        try:
            value = json.loads(value)
            list_items = value["e"]
            #  since we created it and it only has one element
            v = list_items[0]["v"]
            key = "o:"+id+":"+topic
            self.redisDB.add_to_list(key, v)
        except Exception as e:
            logger.error("error adding to redis "+str(e))