"""
Created on Jul 16 14:13 2018

@author: nishit
"""
import json
import logging

import os

from optimization.ESSDataReceiver import ESSDataReceiver
from optimization.optimizationDataReceiver import OptimizationDataReceiver


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class InputController:

    def __init__(self, id, input_config_parser, config, timesteps):
        self.optimization_data = {}
        self.prediction_subscriber={}
        self.input_config_parser = input_config_parser
        self.config = config
        self.timesteps = timesteps
        self.id=id
        self.load_forecast = False
        self.pv_forecast = False
        # need to get a internal_forecast from input config parser
        self.ess_data = False
        self.parse_input_config()

        self.set_timestep_data()
        self.set_params()

        """for predictions"""
        topics = []
        if self.load_forecast:
            load_forecast_topic = config.get("IO", "load.forecast.topic")
            load_forecast_topic = json.loads(load_forecast_topic)
            topics.append(load_forecast_topic)
        else:
            self.read_input_data(id, "P_Load_Forecast", "p_load.txt")
        if self.pv_forecast:
            pv_forecast_topic = config.get("IO", "pv.forecast.topic")
            pv_forecast_topic = json.loads(pv_forecast_topic)
            topics.append(pv_forecast_topic)
        else:
            self.read_input_data(id, "P_PV_Forecast", "p_pv.txt")
        if len(topics) > 0:
            self.prediction_subscriber[self.id] = OptimizationDataReceiver(topics, config)
        else:
            self.prediction_subscriber[self.id] = None

        # ESS data
        if self.ess_data:
            topic = self.input_config_parser.get_params("SoC_Value")
            self.ess_data_receiver = ESSDataReceiver(False, topic, config)

    def set_timestep_data(self):
        i = 0
        T = []
        T_SoC = []
        while i < self.timesteps:
            T.append(i)
            T_SoC.append(i)
            i += 1
        T_SoC.append(i)
        self.optimization_data["N"] = {None: [0]}
        self.optimization_data["T"] = {None: T}
        self.optimization_data["T_SoC"] = {None: T_SoC}
        self.optimization_data["Target"] = {None: 1}
        self.optimization_data["dT"] = {None: 3600}

    def parse_input_config(self):
        data = self.input_config_parser.get_optimization_values()
        self.optimization_data.update(data)
        self.load_forecast = self.input_config_parser.get_forecast_flag("load")
        logger.debug("self.load_forecast: "+ str(self.load_forecast))
        self.pv_forecast = self.input_config_parser.get_forecast_flag("photovoltaic")
        logger.debug("self.pv_forecast: " + str(self.pv_forecast))
        self.ess_data = self.input_config_parser.get_forecast_flag("SoC_Value")
        logger.debug("self.ess_data: " + str(self.ess_data))

    def read_input_data(self, id, topic, file):
        data = {}
        """"/ usr / src / app / optimization / 95c38e56d913 / p_load.txt"""
        logger.debug("This is the id in read_input_data: "+str(id))
        path = os.path.join("/usr/src/app", "optimization", str(id), file)
        rows = []
        i = 0
        try:
            with open(path, "r") as file:
                rows = file.readlines()
        except Exception as e:
            logger.error("Read input file exception: "+str(e))
        for row in rows:
            data[i] = float(row)
            i += 1
        if len(data) == 0:
            logger.error("Data file empty "+topic)
        else:
            self.optimization_data[topic] = data

    def get_data(self, id):
        """needs to be changed"""
        if not self.load_forecast:
            self.read_input_data(id, "P_Load_Forecast", "p_load.txt")
        if not self.pv_forecast:
            self.read_input_data(id, "P_PV_Forecast", "p_pv.txt")
        """until here"""

        pv_check = not self.pv_forecast
        load_check = not self.load_forecast
        while not (pv_check and load_check):
            if self.prediction_subscriber[id]:
                data = self.prediction_subscriber[id].get_data()
                self.optimization_data.update(data)
                if "P_PV_Forecast" in data.keys():
                    pv_check = True
                if "P_Load_Forecast" in data.keys():
                    load_check = True
        if self.ess_data:
            data = self.ess_data_receiver.get_data()
            self.optimization_data.update(data)
        return {None: self.optimization_data.copy()}

    def Stop(self, id):
        if self.prediction_subscriber[id] is not None:
            self.prediction_subscriber[id].exit()

    def set_params(self):
        params = {
            'Q_Load_Forecast': {
                0: 0.0,
                1: 0.0,
                2: 0.0,
                3: 0.0,
                4: 0.0,
                5: 0.0,
                6: 0.0,
                7: 0.0,
                8: 0.0,
                9: 0.0,
                10: 0.0,
                11: 0.0,
                12: 0.0,
                13: 0.0,
                14: 0.0,
                15: 0.0,
                16: 0.0,
                17: 0.0,
                18: 0.0,
                19: 0.0,
                20: 0.0,
                21: 0.0,
                22: 0.0,
                23: 0.0},
            'Price_Forecast': {
                0: 34.61,
                1: 33.28,
                2: 33.03,
                3: 32.93,
                4: 31.96,
                5: 33.67,
                6: 40.45,
                7: 47.16,
                8: 47.68,
                9: 46.23,
                10: 43.01,
                11: 39.86,
                12: 37.64,
                13: 37.14,
                14: 39.11,
                15: 41.91,
                16: 44.11,
                17: 48.02,
                18: 51.65,
                19: 48.73,
                20: 43.56,
                21: 38.31,
                22: 37.66,
                23: 36.31},
            'Grid_VGEN': {None: 0.4},
            'Grid_R': {None: 0.67},
            'Grid_X': {None: 0.282},
            'Grid_dV_Tolerance': {None: 0.1}
        }
        if not self.ess_data and not "ESS_SoC_Value" in self.optimization_data.keys():
            params['ESS_SoC_Value'] = {0: 0.35}
        self.optimization_data.update(params)