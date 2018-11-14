"""
Created on Jul 16 14:13 2018

@author: nishit
"""
import json
import logging

import os
import re

from optimization.SoCValueDataReceiver import SoCValueDataReceiver
from optimization.genericDataReceiver import GenericDataReceiver
from optimization.internalDataReceiver import InternalDataReceiver

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)


class InputController:

    def __init__(self, id, input_config_parser, config, control_frequency, horizon_in_steps, dT_in_seconds):
        self.stop_request = False
        self.optimization_data = {}
        self.internal_subscriber = {}
        self.input_config_parser = input_config_parser
        logger.debug("Config parser: " + str(self.input_config_parser))
        self.config = config
        self.control_frequency = control_frequency
        self.horizon_in_steps = horizon_in_steps
        self.dT_in_seconds = dT_in_seconds
        self.id = id
        self.prediction_mqtt_flags = {}
        self.non_prediction_mqtt_flags = {}
        self.external_mqtt_flags = {}
        # need to get a internal_forecast from input config parser
        self.soc_value_data_mqtt = False
        self.generic_data_mqtt = {}
        self.generic_names = None
        self.parse_input_config()

        self.set_timestep_data()
        # self.set_params()

        """for predictions"""
        topics = []
        for topic, flag in self.prediction_mqtt_flags.items():
            if flag:
                """ should be prediction topic instead of load"""
                load_forecast_topic = config.get("IO", "load.forecast.topic")
                load_forecast_topic = json.loads(load_forecast_topic)
                topics.append(load_forecast_topic)
                break
        for topic, flag in self.non_prediction_mqtt_flags.items():
            if flag:
                if topic == "P_PV":
                    pv_forecast_topic = config.get("IO", "pv.forecast.topic")
                    pv_forecast_topic = json.loads(pv_forecast_topic)
                    topics.append(pv_forecast_topic)

        if len(topics) > 0:
            self.internal_subscriber[self.id] = InternalDataReceiver(topics, config, self.id)
        else:
            self.internal_subscriber[self.id] = None

        # ESS data
        self.external_data_receiver = {}
        for topic, flag in self.external_mqtt_flags.items():
            if flag:
                if topic == "SoC_Value":
                    params = self.input_config_parser.get_params("SoC_Value")
                    logger.debug("params for MQTT SoC_Value: " + str(params))
                    self.external_data_receiver[topic] = SoCValueDataReceiver(False, params, config, self.id)

        self.generic_data_receiver = {}
        if len(self.generic_data_mqtt) > 0:
            for generic_name, mqtt_flag in self.generic_data_mqtt.items():
                if mqtt_flag:
                    topic = self.input_config_parser.get_params(generic_name)
                    self.generic_data_receiver[generic_name] = GenericDataReceiver(False, topic, config, generic_name,
                                                                                   self.id)

    def get_forecast_files(self, id, output):
        f = []
        mypath = os.path.join("/usr/src/app/optimization/resources", str(id), "file")
        logger.debug("This is mypath: " + str(mypath))

        for (dirpath, dirnames, filenames) in os.walk(mypath):
            f.extend(filenames)
            break
        logger.debug("These are the names in " + str(id) + ": " + str(f))

        for filenames in f:
            if output in filenames:
                file = filenames
                logger.debug("File name: " + str(file))
                # filenames = re.sub('.txt', '_Forecast', str(filenames))
                filenames = re.sub('.txt', '', str(filenames))
                topic = filenames
                logger.debug("Topic: " + str(topic))
                self.read_input_data(id, topic, file)

    def set_timestep_data(self):
        i = 0
        T = []
        T_SoC = []
        while i < self.horizon_in_steps:
            T.append(i)
            T_SoC.append(i)
            i += 1
        T_SoC.append(i)
        self.optimization_data["N"] = {None: [0]}
        self.optimization_data["T"] = {None: T}
        self.optimization_data["T_SoC"] = {None: T_SoC}
        # self.optimization_data["Target"] = {None: 1}
        self.optimization_data["dT"] = {None: self.dT_in_seconds}

    ######big change

    def parse_input_config(self):
        data = self.input_config_parser.get_optimization_values()
        self.optimization_data.update(data)
        self.prediction_names = self.input_config_parser.get_prediction_names()
        logger.debug("self.prediction_names: " + str(self.prediction_names))
        if self.prediction_names is not None and len(self.prediction_names) > 0:
            for prediction_name in self.prediction_names:
                self.prediction_mqtt_flags[prediction_name] = self.input_config_parser.get_forecast_flag(
                    prediction_name)
        self.non_prediction_names = self.input_config_parser.get_non_prediction_names()
        logger.debug("self.non_prediction_names" + str(self.non_prediction_names))
        if self.non_prediction_names is not None and len(self.non_prediction_names) > 0:
            for non_prediction_name in self.non_prediction_names:
                self.non_prediction_mqtt_flags[non_prediction_name] = self.input_config_parser.get_forecast_flag(
                    non_prediction_name)
        self.external_names = self.input_config_parser.get_external_names()
        logger.debug("self.external_names" + str(self.external_names))
        if self.external_names is not None and len(self.external_names) > 0:
            for external_name in self.external_names:
                self.external_mqtt_flags[external_name] = self.input_config_parser.get_forecast_flag(
                    external_name)
        self.generic_names = self.input_config_parser.get_generic_data_names()
        logger.debug("self.generic_names" + str(self.generic_names))
        if self.generic_names is not None and len(self.generic_names) > 0:
            for generic_name in self.generic_names:
                self.generic_data_mqtt[generic_name] = self.input_config_parser.get_forecast_flag(generic_name)

    def read_input_data(self, id, topic, file):
        data = {}
        """"/ usr / src / app / optimization / resources / 95c38e56d913 / p_load.txt"""
        path = os.path.join("/usr/src/app", "optimization/resources", str(id), "file", file)
        logger.debug("Data path: " + str(path))
        rows = []
        i = 0
        try:
            with open(path, "r") as file:
                rows = file.readlines()
        except Exception as e:
            logger.error("Read input file exception: " + str(e))
        for row in rows:
            data[i] = float(row)
            i += 1
        if len(data) == 0:
            logger.error("Data file empty " + topic)
        else:
            self.optimization_data[topic] = data

    def get_data(self, id):
        name_check = {}
        for prediction_name, mqtt_flag in self.prediction_mqtt_flags.items():
            logger.debug("prediction_name: " + str(prediction_name))
            if mqtt_flag:
                name_check[prediction_name] = False
            else:
                self.read_input_data(id, prediction_name, prediction_name + ".txt")
        for non_prediction_name, mqtt_flag in self.non_prediction_mqtt_flags.items():
            logger.debug("non_prediction_name: " + str(non_prediction_name))
            if mqtt_flag:
                name_check[non_prediction_name] = False
            else:
                self.read_input_data(id, non_prediction_name, non_prediction_name + ".txt")
        logger.info("name_check = " + str(name_check))
        while not self.check(name_check) and not self.stop_request:
            if self.internal_subscriber[id]:
                logger.debug("Entered the prediction subscriber")
                data = self.internal_subscriber[id].get_data()
                data = self.set_indexing(data)
                self.optimization_data.update(data)
                for key in data.keys():
                    if key in name_check.keys():
                        name_check[key] = True
        logger.debug("external mqtt data " + str(self.external_mqtt_flags))
        if self.external_mqtt_flags is not None:
            for external_name, mqtt_flag in self.external_mqtt_flags.items():
                if not mqtt_flag:
                    logger.debug("external name: " + str(external_name))
                    if external_name is not "SoC_Value":
                        self.read_input_data(id, external_name, external_name + ".txt")
                else:
                    logger.debug("external mqtt True " + str(external_name))
                    data = self.external_data_receiver[external_name].get_data()
                    data = self.set_indexing(data)
                    logger.debug("SoC_Value MQTT data: " + str(data))
                    self.optimization_data.update(data)
        logger.debug("self.generic_data_mqtt " + str(self.generic_data_mqtt))
        if self.generic_data_mqtt is not None:
            logger.debug("Entered self.generic_data_mqtt")
            for generic_name, mqtt_flag in self.generic_data_mqtt.items():
                logger.debug("generic_name: " + str(generic_name))
                if not mqtt_flag:
                    logger.debug("generic_name not mqtt flag" + str(generic_name))
                    self.read_input_data(id, generic_name, generic_name + ".txt")
                else:
                    data = self.generic_data_receiver[generic_name].get_data()
                    data = self.set_indexing(data)
                    self.optimization_data.update(data)
        return {None: self.optimization_data.copy()}

    def check(self, name_check):
        result = True
        for flag in name_check.values():
            result = result and flag
        return result

    def Stop(self, id):
        self.stop_request = True
        if self.internal_subscriber[id] is not None:
            self.internal_subscriber[id].exit()
        for external_name in self.external_data_receiver.keys():
            self.external_data_receiver[external_name].exit()
        for generic_name in self.generic_data_receiver.keys():
            self.generic_data_receiver[generic_name].exit()

    def set_indexing(self, data):
        new_data = {}
        for name, value in data.items():
            indexing = self.input_config_parser.get_variable_index(name)
            # default indexing will be set to "index" in baseDataReceiver
            if indexing == "None":
                if len(value) >= 1:
                    if isinstance(value, dict):
                        v = value[0]  # 0 is the key
                        new_data[name] = {None: v}
        data.update(new_data)
        return data

    """def set_params(self):
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
        if not self.soc_value_data_mqtt and not "SoC_Value" in self.optimization_data.keys():
            params['SoC_Value'] = {0: 0.35}
        self.optimization_data.update(params)"""
