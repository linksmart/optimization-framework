import logging
import paho.mqtt.client as mqtt
import time

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class MQTTClient:
    def __init__(self, host, mqttPort, keepalive=60):
        self.host =host
        self.port=mqttPort
        self.keepalive=keepalive
        self.receivedMessages = []



        self.client = mqtt.Client(client_id="PROFESS")
        #client.username_pw_set("<<tenant>>/<<username>>", "<<password>>")
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_connect = self.on_connect

        logger.info("Trying to connect to the MQTT broker")
        try:
            self.client.connect(self.host, self.port, self.keepalive)

        except Exception as e:
            logger.error(e)

        #self.client.loop_forever()
        self.client.loop_start()
        #publish("s/us", "100,Python MQTT,c8y_MQTTDevice", True)
        #publish("s/us", "110,S123456789,MQTT test model,Rev0.1")
        #client.subscribe("s/ds")
        #sendMeasurements()

        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.


    def on_connect(self, client, userdata, flags, rc):
        logger.info("Connected with result code " + str(rc))
        #if rc == 0:
        logger.info("Connected to the broker")

            #self.client.subscribe("test/#")
        #else:
            #logger.error("Connection to the broker failed")

    def on_message(self,client, userdata, message):
        logger.info(message.topic + " " + str(message.payload))
        if (message.payload.startswith("something")):
            logger.info("Input operation")


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
                time.sleep(0.25)

    def on_publish(self,client, userdata, mid):
        self.receivedMessages.append(mid)

    def MQTTExit(self):
        logger.debug("Disconnecting MQTT")
        self.client.disconnect()
        logger.debug("Disconnected from the MQTT clients")
        self.client.loop_stop()
        logger.debug("MQTT service disconnected")