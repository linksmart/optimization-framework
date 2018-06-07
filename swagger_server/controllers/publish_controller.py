"""
Created on Jun 07 14:09 2018

@author: nishit
"""
import json
import logging

import connexion

from IO.MQTTClient import MQTTClient

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

def mqtt_forecast_publish(mqtt_publish):
    if connexion.request.is_json:
        logger.info("Starting the system")
        d = connexion.request.get_json()
        logger.info("json = "+str(d)+" type "+str((type(d))))
        data = json.dumps(d)
        mqtt = MQTTClient("optimizationframework_mosquitto_1",1883)
        mqtt.sendResults("load_forecast",json)
        try:
            logger.info("Sending results to this topic: "+"load_forecast")
            mqtt.publish("load_forecast", data, True) #using publish beacuse want to set waitforAck=true
            logger.debug("Results published")
        except Exception as e:
            logger.error(e)
    return "sucessfull"
