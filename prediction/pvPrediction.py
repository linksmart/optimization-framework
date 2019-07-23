"""
Created on Aug 03 14:02 2018

@author: nishit
"""
import json

from optimization.pvForecastPublisher import PVForecastPublisher
from utils_intern.messageLogger import MessageLogger


class PVPrediction:

    def __init__(self, config, input_config_parser, id, control_frequency, horizon_in_steps, dT_in_seconds, name):
        self.logger = MessageLogger.get_logger(__name__, id)
        self.logger.debug("PV prediction class")
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
            self.logger.error("City or country not present in pv meta")

        location = {"city":city,"country":country}

        maxPV = float(opt_values["PV_Inv_Max_Power"][None])
        pv_forecast_topic = config.get("IO", "forecast.topic")
        pv_forecast_topic = json.loads(pv_forecast_topic)
        pv_forecast_topic["topic"] = pv_forecast_topic["topic"] + name

        self.pv_forecast_pub = PVForecastPublisher(pv_forecast_topic, config, id, maxPV, control_frequency,
                                                   horizon_in_steps, dT_in_seconds, location)
        self.pv_forecast_pub.start()

    def Stop(self):
        self.logger.debug("Stopping pv forecast thread")
        if self.pv_forecast_pub is not None:
            self.pv_forecast_pub.Stop()
        self.logger.debug("pv prediction thread exit")
