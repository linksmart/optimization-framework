"""
Created on Jun 27 17:36 2018

@author: nishit
"""
import threading
import time
from abc import ABC, abstractmethod
from queue import Queue

from random import randrange

from IO.ConfigParserUtils import ConfigParserUtils
from IO.MQTTClient import MQTTClient
from IO.ZMQClient import ZMQClient
from utils_intern.messageLogger import MessageLogger
from IO.redisDB import RedisDB


class DataReceiver(ABC):

    def __init__(self, internal, topic_params, config, emptyValue={}, id=None, section=None, prepare_topic_qos=True, sub_pub=False):
        super(DataReceiver, self).__init__()
        self.q_bdr = Queue(maxsize=0)
        self.q_dr = Queue(maxsize=0)
        self.logger = MessageLogger.get_logger(__name__, id)
        self.stop_request = False
        self.internal = internal
        self.topic_params = topic_params
        self.prepare_topic_qos = prepare_topic_qos
        self.emptyValue = emptyValue
        self.data = self.emptyValue.copy()
        self.data_update = False
        self.config = config
        self.channel = "MQTT"
        self.topics = None
        self.port = None
        self.host_params = {}
        self.first_time = 0
        self.last_time = 0
        self.id = id
        self.section = section
        self.redisDB = RedisDB()
        self.sub_pub = sub_pub
        if self.section is None:
            self.section = "IO"
        self.setup()
        if self.channel == "MQTT":
                self.init_mqtt(self.topics)
        elif self.channel == "ZMQ":
            self.init_zmq(self.topics)
        self.data_sync_thread_dr = None
        #self.data_sync_thread_dr = threading.Thread(target=self.data_sync_dr).start()

    def setup(self):
        if self.internal:
            self.channel = self.config.get("IO", "channel")
            self.topics, self.host_params = self.get_internal_channel_params()
        else:
            self.topics, self.host, self.host_params = self.get_external_channel_params()

    def get_external_channel_params(self):
        topic_qos = []
        # read from config
        sub_mqtt = "sub.mqtt.host"
        if self.sub_pub:
            sub_mqtt = "pub.mqtt.host"
        if sub_mqtt in dict(self.config.items(self.section)):
            host = self.config.get(self.section, sub_mqtt)
        else:
            host = self.config.get("IO", "mqtt.host")

        host, host_params, qos, topic, self.port = ConfigParserUtils.extract_host_params(host, self.port, self.topic_params,
                                                                    self.config, self.section)
        if topic:
            topic_qos.append((topic, qos))
        return (topic_qos, host, host_params)

    def get_internal_channel_params(self):
        if self.channel == "MQTT":
            sub_mqtt = "sub.mqtt.host"
            if self.sub_pub:
                sub_mqtt = "pub.mqtt.host"
            topic_qos = []
            host_params = {}
            if self.prepare_topic_qos:
                for k, v in self.topic_params.items():
                    if k == "topic":
                        topic_qos.append((v + "/" + self.id,1))
                    elif k == "mqtt.port":
                        self.port = v
            elif isinstance(self.topic_params, list):
                topic_qos = self.topic_params
                self.port = self.config.get("IO", "mqtt.port")
            if sub_mqtt in dict(self.config.items("IO")):
                self.host = self.config.get("IO", sub_mqtt)
            if "mqtt.host" in dict(self.config.items("IO")):
                self.host = self.config.get("IO", "mqtt.host")
            host_params["username"] = self.config.get("IO", "mqtt.username", fallback=None)
            host_params["password"] = self.config.get("IO", "mqtt.password", fallback=None)
            host_params["ca_cert_path"] = self.config.get("IO", "mqtt.ca.cert.path", fallback=None)
            host_params["insecure_flag"] = bool(self.config.get("IO", "mqtt.insecure.flag", fallback=False))
            return (topic_qos, host_params)
        elif self.channel == "ZMQ":
            topics = []
            for k, v in self.topic_params.items():
                if k == "topic":
                    topics.append(v + "/" + self.id)
            self.port = self.config.get("IO", "zmq.sub.port")
            self.host = self.config.get("IO", "zmq.host")
            return (topics, None)

    def init_mqtt(self, topic_qos):
        self.logger.info("Initializing mqtt subscription client")
        #if we set it to false here again then it may overwrite previous true value
        #self.redisDB.set("Error mqtt"+self.id, False)
        try:
            if not self.port:
                self.port = 1883
                #read from config
            self.client_id = "client_receive" + str(randrange(100000)) + str(time.time()).replace(".","")
            self.mqtt = MQTTClient(str(self.host), self.port, self.client_id, username=self.host_params["username"],
                                   password=self.host_params["password"], ca_cert_path=self.host_params["ca_cert_path"],
                                   set_insecure=self.host_params["insecure_flag"], id=self.id)

            self.mqtt.subscribe_to_topics(topic_qos, self.on_msg_received)
            self.logger.info("successfully subscribed")
        except Exception as e:
            self.logger.error(e)
            # error for mqtt will be caught by parent
            raise e

    def init_zmq(self, topics):
        self.logger.info("Initializing zmq subscription client")
        self.zmq = ZMQClient(self.host, None, self.port)
        self.zmq.init_subscriber(topics, self.id)

    @abstractmethod
    def on_msg_received(self, payload):
        pass

    def get_data_update(self):
        return self.data_update

    def set_data_update(self, data_update):
        self.data_update = data_update

    def get_mqtt_data(self, require_updated, clearData):
        if require_updated == 1 and not self.data:
            require_updated = 0
        ctr = 0
        self.read_from_bdr()
        while require_updated == 0 and not self.get_data_update() and not self.stop_request and not self.redisDB.get("End ofw") == "True":
            if ctr >= 9:
                ctr = 0
                self.logger.debug("wait for data "+str(self.topics)+str(self.get_data_update())+
                                  " "+str(self.stop_request)+" "+str(self.redisDB.get("End ofw") == "True"))
            ctr += 1
            time.sleep(0.5)
            self.read_from_bdr()
        self.write_to_dr()
        return self.get_and_update_data(clearData)

    def exit(self):
        self.stop_request = True
        try:
            if self.channel == "MQTT":
                self.mqtt.MQTTExit()
            elif self.channel == "ZMQ":
                self.zmq.stop()
            self.logger.info("dataReceiver safe exit")
        except Exception as e:
            self.logger.warning(str(e))

    def get_zmq_msg(self, clearData):
        while True and not self.stop_request:
            self.logger.debug("get zmq msg")
            flag, topic, message = self.zmq.receive_message()
            self.logger.debug("zmq subscription msg received for topic "+str(topic)+" for id "+str(self.id))
            if flag:
                self.on_msg_received(message)
                break
            time.sleep(1)
        return self.get_and_update_data(clearData)

    def get_and_update_data(self, clearData):
        new_data = self.data.copy()
        self.set_data_update(False)
        if clearData:
            self.clear_data()
        self.logger.debug("new_data "+str(new_data))
        return new_data

    def clear_data(self):
        self.data = self.emptyValue.copy()

    def get_data(self, require_updated=0, clearData=False):
        """

        :param require_updated: 0 -> wait for new data
                                1 -> wait for new data if no prev data
                                2 -> return prev data, even if empty
        :return:
        """
        data = {}
        if self.channel == "MQTT":
            data = self.get_mqtt_data(require_updated, clearData)
        elif self.channel == "ZMQ":
            data = self.get_zmq_msg(clearData)
        return data

    def data_sync_dr(self):
        while not self.stop_request and not not self.redisDB.get("End ofw") == "True":
            self.read_from_bdr()
            time.sleep(1)

    def read_from_bdr(self):
        if not self.q_bdr.empty():
            try:
                new_data = self.q_bdr.get_nowait()
                self.logger.debug("new data "+str(new_data))
                self.q_bdr.task_done()
                if "data_update" in new_data.keys():
                    self.data_update = new_data["data_update"]
                if "first_time" in new_data.keys():
                    self.first_time = new_data["first_time"]
                if "last_time" in new_data.keys():
                    self.last_time = new_data["last_time"]
                if "data" in new_data.keys():
                    self.data = new_data["data"]
            except Exception:
                self.logger.error("Queue empty")
        else:
            self.logger.debug("bdr Queue empty")

    def write_to_dr(self):
        try:
            new_data = {
                "BaseDataReceiver": {
                "data_update" : self.data_update,
                "first_time": self.first_time,
                "last_time" : self.last_time,
                "data" : self.data.copy()
                }
            }
            self.q_dr.put(new_data)
        except Exception as e:
            self.logger.error(e)