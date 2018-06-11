import logging
from IO.MQTTClient import MQTTClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class OutputController:

    def __init__(self, output_config):

        logger.info("Output Class started")
        self.output_config=output_config
        self.mqtt={}
        self.client_id = "PROFESS"

        ###Connection to the mqtt broker
        try:
            for key, value in self.output_config.items():
                for key2, value2 in value.items():
                    #if value2["mqtt"]["host"]:
                    #    logger.debug("True")
                    #else:
                    #    logger.debug("False")
                    #if value2["mqtt"]["host"].isspace():
                    #    logger.debug("True")
                    #else:
                    #    logger.debug("False")
                    if  (value2["mqtt"]["host"] or value2["mqtt"]["host"].isspace()):
                        #compare="True"
                        host=value2["mqtt"]["host"]
                        #logger.debug("Host configuration: " + str(host))
                        #logger.debug("Self.mqtt: "+str(self.mqtt))

                        if bool(self.mqtt):
                            #logger.debug("True")
                            if host in self.mqtt:
                                logger.debug("Already connected to the host "+host)
                            else:
                                logger.debug("Creating mqtt client with the host: " + str(host))
                                self.mqtt[str(host)] = MQTTClient(str(host), 1883, self.client_id)
                        else:
                            #logger.debug("False")
                            logger.debug("Creating mqtt client with the host: " + str(host))
                            self.mqtt[str(host)] = MQTTClient(str(host), 1883, self.client_id)
                    logger.debug("Self.mqtt: " + str(self.mqtt))
        except Exception as e:
            logger.error(e)




    def publishController(self, data):

        try:
            #logger.debug("These are the keys of output_config: "+str(output_config.keys()))
            logger.debug("These are the keys of data: " + str(data.keys()))
            for key, value in self.output_config.items():
                #logger.debug("Key: " + key)
                for key2, value2 in value.items():
                    #logger.debug("Key2: "+key2)
                    #logger.debug("MQTT Topic: "+value2["mqtt"]["topic"])
                    if key2 in data:
                        #compare="True"
                        topic=value2["mqtt"]["topic"]+"/"+key2
                        host = value2["mqtt"]["host"]
                        #logger.debug("Published to this topic")
                        #logger.debug("Value: "+str(data.get(key2)))
                        self.mqtt[str(host)].sendResults(topic, str(data.get(key2)))
        except Exception as e:
            logger.error(e)






    def makeFile(self):
        return 0
