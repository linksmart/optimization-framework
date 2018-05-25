import logging
from IO.MQTTClient import MQTTClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class OutputController:

    def __init__(self):

        logger.info("Output Class started")

        ###Connection to the mqtt broker

        self.mqtt=MQTTClient("optiframework_mosquitto_1",1883)


    def publishController(self, data):
        topic="myTopic"
        for key,value in data.items():
            #logger.info(str(value))
            self.mqtt.sendResults(key, str(value))
        #logger.info("Ouput data " + str(data))
        #logger.info("Veamos: " + str(data.get("P_PV_Output")))





    def makeFile(self):
        return 0
