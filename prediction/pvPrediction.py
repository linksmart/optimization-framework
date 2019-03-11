"""
Created on Aug 03 14:02 2018

@author: nishit
"""
import json
import logging

from IO.locationData import LocationData
from optimization.pvForecastPublisher import PVForecastPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class PVPrediction:

    def __init__(self, config, input_config_parser, id, control_frequency, horizon_in_steps, dT_in_seconds, name):
        logger.debug("PV prediction class")
        self.config = config
        self.input_config_parser = input_config_parser
        raw_pv_data_topic = input_config_parser.get_params("P_PV")
        """
        subscribe mqtt to get raw pv data
        setup q to send data to internal mqtt/zmq for predicted pv data
        """

        opt_values = input_config_parser.get_optimization_values()

        city = "Bonn"
        country = "Germany"
        try:
            city = opt_values["City"][None]
            country = opt_values["Country"][None]
        except Exception:
            logger.error("City or country not present in pv meta")

        location_data = LocationData(config)
        lat, lon = location_data.get_city_coordinate(city, country)

        if lat is None or lon is None:
            lat = 50.7374
            lon = 7.0982
            logger.error("Error getting location info, setting to bonn, germany")

        maxPV = float(opt_values["PV_Inv_Max_Power"][None])
        pv_forecast_topic = config.get("IO", "forecast.topic")
        pv_forecast_topic = json.loads(pv_forecast_topic)
        pv_forecast_topic["topic"] = pv_forecast_topic["topic"] + name

        self.pv_forecast_pub = PVForecastPublisher(pv_forecast_topic, config, id, lat, lon, maxPV, control_frequency,
                                                   horizon_in_steps, dT_in_seconds)
        self.pv_forecast_pub.start()

    def Stop(self):
        logger.debug("Stopping pv forecast thread")
        if self.pv_forecast_pub is not None:
            self.pv_forecast_pub.Stop()
        logger.debug("pv prediction thread exit")
