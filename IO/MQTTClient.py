import logging
import paho.mqtt.client as mqtt
import time

from utils.messageLogger import MessageLogger

class MQTTClient:

    def __init__(self, host, mqttPort, client_id, keepalive=60, username=None, password=None, ca_cert_path=None,
                 set_insecure=False, id=None):
        self.logger = MessageLogger.get_logger(__file__, id)
        self.host =host
        self.port = int(mqttPort)
        self.keepalive=keepalive
        self.receivedMessages = []
        self.topic_ack_wait = []
        self.callback_function = None
        self.client_id = client_id
        self.id=id
        self.client = mqtt.Client(client_id)
        if username is not None and password is not None:
            self.logger.debug("u "+username+" p "+password)
            self.client.username_pw_set(username, password)
        if ca_cert_path is not None and len(ca_cert_path) > 0:
            self.logger.debug("ca " + ca_cert_path)
            self.client.tls_set(ca_certs=ca_cert_path)
            self.logger.debug("insec "+str(set_insecure))
            self.client.tls_insecure_set(set_insecure)
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_connect = self.on_connect
        self.client.on_subscribe = self.on_subscribe

        self.logger.info("Trying to connect to the MQTT broker "+str(self.host)+" "+str(self.port))
        try:
            self.client.connect(self.host, self.port, self.keepalive)

        except Exception as e:
            msg = "Invalid MQTT host "+str(self.host)+" "+str(self.port)
            self.logger.error("Error connecting client "+str(self.host)+" "+str(self.port) + " " + str(e))
            raise InvalidMQTTHostException(msg)

        #self.client.loop_forever()
        self.client.loop_start()

        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.


    def on_connect(self, client, userdata, flags, rc):
        self.logger.info("Connected with result code " + str(rc))
        #if rc == 0:
        self.logger.info("Connected to the broker")


    def on_message(self,client, userdata, message):
        self.callback_function(message.payload.decode())


    def sendResults(self, topic, data, qos):
        try:
            self.logger.debug("Sending results to this topic: "+topic)
            self.publish(topic, data, qos=qos)
            self.logger.debug("Results published")
        except Exception as e:
            self.logger.error(e)

    def publish(self, topic, message, waitForAck=False, qos=2):
        mid = self.client.publish(topic, message, qos)[1]
        if (waitForAck):
            while mid not in self.receivedMessages:
                self.logger.debug("waiting for pub ack for topic "+str(topic))
                time.sleep(0.25)

    def on_publish(self,client, userdata, mid):
        self.receivedMessages.append(mid)

    def MQTTExit(self):
        self.logger.debug("Disconnecting MQTT")
        self.client.disconnect()
        self.logger.debug("Disconnected from the MQTT clients")
        self.client.loop_stop()
        self.logger.debug("MQTT service disconnected")

    def subscribe(self, topics_qos, callback_function):
        # topics_qos is a list of tuples. eg [("topic",0)]
        try:
            self.logger.info("Subscribing to topics with qos: " + str(topics_qos))
            result, mid = self.client.subscribe(topics_qos)
            if result == 0:
                self.logger.debug("Subscribed to topics: "+ str(topics_qos) + " result = " + str(result) + " , mid = " + str(mid))
                self.topic_ack_wait.append(tuple([str(topics_qos), mid]))
                self.logger.debug("sub ack wait = "+str(self.topic_ack_wait))
                self.callback_function = callback_function
                logging.info("callback functions set")
            else:
                logging.info("error on subscribing " + str(result))
        except Exception as e:
            self.logger.error(e)

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """check mid values from topic ack list"""
        if len(self.topic_ack_wait) > 0:
            for i, m in enumerate(self.topic_ack_wait):
                if m[1] == mid:
                    self.topic_ack_wait.pop(i)

    def subscribe_ack_wait(self):
        count = 0
        while count < 10:
            if len(self.topic_ack_wait) == 0:
                return True
            else:
                self.logger.info("topic ack wait len = "+str(len(self.topic_ack_wait)))
            time.sleep(1)
            count+=1
        self.topic_ack_wait.pop()
        return False


class InvalidMQTTHostException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)