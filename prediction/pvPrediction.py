"""
Created on Aug 03 14:02 2018

@author: nishit
"""
import json
import logging

from optimization.pvForecastPublisher import PVForecastPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class PVPrediction:

    def __init__(self, config, input_config_parser, id):
        self.config = config
        self.input_config_parser = input_config_parser
        raw_pv_data_topic = input_config_parser.get_params("P_PV")
        """
        subscribe mqtt to get raw pv data
        setup q to send data to internal mqtt/zmq for predicted pv data
        """

        pv_forecast_topic = config.get("IO", "pv.forecast.topic")
        pv_forecast_topic = json.loads(pv_forecast_topic)
        logger.debug("id 4 = " + str(id))
        self.pv_forecast_pub = PVForecastPublisher(pv_forecast_topic, config, id)
        self.pv_forecast_pub.start()

    def Stop(self):
        logger.info("start pv prediction thread exit")
        logger.info("Stopping pv forecast thread")
        self.pv_forecast_pub.Stop()
        logger.info("pv prediction thread exit")
