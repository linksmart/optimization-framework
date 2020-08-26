import json

import time

from senml import senml

from IO.ConfigParserUtils import ConfigParserUtils
from IO.MQTTClient import MQTTClient
from IO.redisDB import RedisDB
from random import randrange

from utils_intern.messageLogger import MessageLogger

class OutputController:

    def __init__(self, id=None, output_config=None):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.logger.info("Output Class started")
        self.output_config = output_config
        self.mqtt = {}
        self.redisDB = RedisDB()
        self.mqtt_params = {}
        self.output_mqtt = {}
        self.id = id
        self.logger.debug("output_config: " + str(self.output_config) + " " + str(type(self.output_config)))
        if self.output_config is not None:
            self.mqtt_params = ConfigParserUtils.extract_mqtt_params_output(self.output_config, "error_calculation", False)
            self.logger.debug("params = " + str(self.mqtt_params))
            self.init_mqtt()

    def init_mqtt(self):
        ###Connection to the mqtt broker
        self.logger.debug("Starting init mqtt")
        self.redisDB.set("Error mqtt" + self.id, False)
        try:
            for key, value in self.mqtt_params.items():
                self.logger.debug("key " + str(key) + " value " + str(value))

                # self.output_mqtt[key2] = {"host":host, "topic":topic, "qos":qos}
                client_id = "client_publish" + str(randrange(100000)) + str(time.time()).replace(".", "")
                host = str(value["host"])
                port = value["mqtt.port"]
                self.logger.debug("client " + client_id)
                self.logger.debug("host " + host)
                self.logger.debug("port " + str(port))
                client_key = host+":"+str(port)
                if client_key not in self.mqtt.keys():
                    self.mqtt[client_key] = MQTTClient(str(host), port, client_id,
                                            username=value["username"], password=value["password"],
                                            ca_cert_path=value["ca_cert_path"], set_insecure=value["insecure"], id=self.id)
            self.logger.info("successfully subscribed")
        except Exception as e:
            self.logger.debug("Exception while starting mqtt")
            self.redisDB.set("Error mqtt" + self.id, True)
            self.logger.error(e)

    def publish_data(self, id, data, dT):
        self.logger.debug("output data : "+ str(data))
        data = self.convert_to_nested_dict(data)
        self.logger.debug("output data list converted : " + str(data))
        current_time = int(time.time())
        try:
            senml_data = self.senml_message_format(data, current_time, dT)
            for mqtt_key, value in senml_data.items():
                v = json.dumps(value)
                # self.logger.debug("key: "+str(key))
                # self.logger.debug("mqtt params: " + str(self.mqtt_params.keys()))
                if mqtt_key in self.mqtt_params.keys():
                    value2 = self.mqtt_params[mqtt_key]
                    topic = value2["topic"]
                    host = value2["host"]
                    port = value2["mqtt.port"]
                    qos = value2["qos"]
                    client_key = host + ":" + str(port)
                    self.mqtt[client_key].sendResults(topic, v, qos)
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

    def senml_message_format(self, data, current_time, dT):
        new_data = {}
        # self.logger.debug("data for senml "+str(data))
        for key, value in data.items():
            flag = False
            time = current_time
            u = None
            base = None
            bn, n, val = self.get_bn_n_val(key, value)
            if bn:
                base = senml.SenMLMeasurement()
                base.name = bn
            if key in self.mqtt_params.keys():
                if self.mqtt_params[key]["unit"] is not None:
                    u = self.mqtt_params[key]["unit"]
                """
                else:
                    u = "W"
                """
                flag = self.mqtt_params[key]["horizon_values"]
            meas_list = []
            for v in val:
                meas = senml.SenMLMeasurement()
                meas.name = n
                meas.time = time
                meas.value = v
                if u:
                    meas.unit = u
                meas_list.append(meas)
                time += dT
                if not flag:
                    break  # only want the first value
            if len(meas_list) > 0:
                doc = senml.SenMLDocument(meas_list, base=base)
                new_data[key] = doc.to_json()
        # self.logger.debug("Topic MQTT Senml message: "+str(new_data))
        return new_data

    def convert_to_nested_dict(self, data):
        new_data = {}
        for key, value in data.items():
            if isinstance(value, dict):
                is_multi_index = False
                is_single_index = False
                for k, v in value.items():
                    if isinstance(k, tuple):
                        is_multi_index = True
                    elif isinstance(k, int):
                        is_single_index = True
                    break
                if is_multi_index:
                    datalist = {}
                    for k, v in value.items():
                        i, _ = k
                        if i not in datalist.keys():
                            datalist[i] = []
                        datalist[i].append(v)
                    for k, v in datalist.items():
                        new_data[key+"~"+str(k)] = v
                elif is_single_index:
                    datalist = []
                    for k, v in value.items():
                        datalist.append(v)
                    new_data[key] = datalist
                else:
                    new_data[key] = value
            else:
                new_data[key] = value
        return new_data

    def get_bn_n_val(self, key, value):
        if key in self.mqtt_params.keys():
            bn = self.mqtt_params[key]["base_name"]
        else:
            bn = ""
        if isinstance(value, dict):
            bn, n, val = self.get_names(value)
        else:
            bn, n, val = bn, key, value
        return (bn, n, val)

    def save_to_redis(self, id, data, time):
        try:
            part_key = "o:" + id + ":"
            output_keys = self.redisDB.get_keys_for_pattern(part_key+"*")
            if output_keys is not None:
                for key in output_keys:
                    self.redisDB.remove(key)
            for key, value in data.items():
                key = key.replace("~","/")
                bn, n, val = self.get_bn_n_val(key, value)
                if bn:
                    if bn[len(bn)-1] == "/":
                        n = bn + n
                    else:
                        n = bn + "/" + n
                index = 0
                for v in val:
                    k = part_key + n + ":" + str(index)
                    self.redisDB.set(k, json.dumps({str(time): v}))
                    index += 1
        except Exception as e:
            self.logger.error("error adding to redis " + str(e))

    def get_names(self, dict):
        bn = None
        n = None
        v = None
        if "bn" in dict.keys():
            bn = dict["bn"]
        if "n" in dict.keys():
            n = dict["n"]
        if "v" in dict.keys():
            v = dict["v"]
        return (bn,n,v)