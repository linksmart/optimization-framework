import logging
import paho.mqtt.client as mqtt
import time

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class MQTTClient:
    def __init__(self, host, mqttPort, client_id, keepalive=60):
        self.host =host
        self.port=mqttPort
        self.keepalive=keepalive
        self.receivedMessages = []
        self.topic_ack_wait = []
        self.callback_function = None
        self.client_id = client_id
        self.client = mqtt.Client(client_id)
        #client.username_pw_set("<<tenant>>/<<username>>", "<<password>>")
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_connect = self.on_connect
        self.client.on_subscribe = self.on_subscribe

        logger.info("Trying to connect to the MQTT broker")
        try:
            self.client.connect(self.host, self.port, self.keepalive)

        except Exception as e:
            logger.error("Error connecting client "+str(self.host)+" "+str(self.port)+" "+str(self.keepalive))
            logger.error(e)

        #self.client.loop_forever()
        self.client.loop_start()

        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.


    def on_connect(self, client, userdata, flags, rc):
        logger.info("Connected with result code " + str(rc))
        #if rc == 0:
        logger.info("Connected to the broker")


    def on_message(self,client, userdata, message):
        #logger.debug(message.topic + " " + str(message.payload))
        #if (message.payload.startswith("something")):
            #logger.info("Input operation")
        self.callback_function(message.payload.decode())


    def sendResults(self, topic, data):
        try:
            logger.info("Sending results to this topic: "+topic)
            self.publish(topic, data)
            logger.debug("Results published")
        except Exception as e:
            logger.error(e)

    def publish(self, topic, message, waitForAck=False):
        mid = self.client.publish(topic, message, 2)[1]
        if (waitForAck):
            while mid not in self.receivedMessages:
                logger.info("waiting for pub ack for topic "+str(topic))
                time.sleep(0.25)

    def on_publish(self,client, userdata, mid):
        self.receivedMessages.append(mid)

    def MQTTExit(self):
        logger.debug("Disconnecting MQTT")
        self.client.disconnect()
        logger.debug("Disconnected from the MQTT clients")
        self.client.loop_stop()
        logger.debug("MQTT service disconnected")

    def subscribe(self, topics_qos, callback_function):
        # topics_qos is a list of tuples. eg [("topic",0)]
        try:
            logger.info("Subscribing to topics with qos: " + str(topics_qos))
            result, mid = self.client.subscribe(topics_qos)
            if result == 0:
                logger.debug("Subscribed to topics: "+ str(topics_qos) + " result = " + str(result) + " , mid = " + str(mid))
                self.topic_ack_wait.append(tuple([str(topics_qos), mid]))
                self.callback_function = callback_function
                logging.info("callback functions set")
            else:
                logging.info("error on subscribing " + str(result))
        except Exception as e:
            logger.error(e)

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """check mid values from topic ack list"""
        if len(self.topic_ack_wait) > 0:
            for i, m in enumerate(self.topic_ack_wait):
                if m[1] == mid:
                    self.topic_ack_wait.pop(i)

    def subscribe_ack_wait(self):
        count = 0
        while count<100:
            if len(self.topic_ack_wait) == 0:
                return True
            else:
                logger.info("topic ack wait len = "+str(len(self.topic_ack_wait)))
            time.sleep(1)
            count+=1
        return False
