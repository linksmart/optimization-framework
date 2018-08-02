"""
Created on Jul 16 14:13 2018

@author: nishit
"""
import json
import logging

import os

from optimization.optimizationDataReceiver import OptimizationDataReceiver


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class InputController:

    def __init__(self, input_config, config, timesteps):
        self.optimization_data = {}
        self.input_config = input_config
        self.config = config
        self.timesteps = timesteps
        self.load_forecast = False
        self.pv_forecast = False
        self.parse_input_config(input_config)

        self.set_timestep_data()
        self.set_params()

        topics = []
        #self.load_forecast = False
        if self.load_forecast:
            load_forecast_topic = config.get("IO", "load.forecast.topic")
            load_forecast_topic = json.loads(load_forecast_topic)
            topics.append(load_forecast_topic)
        else:
            self.read_input_data("P_Load_Forecast", "loadForecast.txt")
        if self.pv_forecast:
            pv_forecast_topic = config.get("IO", "pv.forecast.topic")
            pv_forecast_topic = json.loads(pv_forecast_topic)
            topics.append(pv_forecast_topic)
        else:
            self.read_input_data("P_PV_Forecast", "pvForecast.txt")
        if len(topics) > 0:
            self.subscriber = OptimizationDataReceiver(topics, config)
        else:
            self.subscriber = None

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

    def parse_input_config(self, input_config):
        data = {}
        for k, v in input_config.items():
            if isinstance(v, dict):
                for k1, v1 in v.items():
                    if k1 == "meta":
                        for k2, v2 in v1.items():
                            v2 = float(v2)
                            if v2.is_integer():
                                v2 = int(v2)
                            if k == "ESS":
                                data[k2] = {0:v2}
                            else:
                                data[k2] = {None:v2}
        self.optimization_data.update(data)
        if "load" in input_config.keys():
            self.load_forecast = bool(input_config["load"]["Internal_Forecast"])
        if "photovoltaic" in input_config.keys():
            self.pv_forecast = bool(input_config["photovoltaic"]["Internal_Forecast"])

    def read_input_data(self, topic, file):
        data = {}
        path = os.path.join("/usr/src/app", "optimization", file)
        rows = []
        i = 0
        try:
            with open(path, "r") as file:
                rows = file.readlines()
        except Exception as e:
            logger.error("read input file exception "+str(e))
        for row in rows:
            data[i] = float(row)
            i += 1
        if len(data) == 0:
            logger.error("Data file empty "+topic)
        else:
            self.optimization_data[topic] = data

    def get_data(self):
        if not self.load_forecast:
            self.read_input_data("P_Load_Forecast", "loadForecast.txt")
        if not self.pv_forecast:
            self.read_input_data("P_PV_Forecast", "pvForecast.txt")
        pv_check = not self.pv_forecast
        load_check = not self.load_forecast
        while not (pv_check and load_check):
            if self.subscriber:
                data = self.subscriber.get_data()
                self.optimization_data.update(data)
                if "P_PV_Forecast" in data.keys():
                    pv_check = True
                if "P_Load_Forecast" in data.keys():
                    load_check = True
        return {None: self.optimization_data.copy()}

    def Stop(self):
        if self.subscriber is not None:
            self.subscriber.exit()

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
            'ESS_SoC_Value': {0: 0.35},
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
        self.optimization_data.update(params)