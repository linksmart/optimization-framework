"""
Created on Aug 17 13:36 2018

@author: nishit
"""
import configparser
import json

import os

from config.configUpdater import ConfigUpdater
from mock_data.mockGenericDataPublisher import MockGenericDataPublisher

from utils_intern.messageLogger import MessageLogger

class MockData:
    def __init__(self, config):
        self.config = config
        self.publishers = {}

    def startMockDataPublisherThreads(self, logger):
        for section in config.sections():
            try:
                if not (section.startswith('IO')):
                    logger.info("topic: " + section)
                    mock_params = {"section" : section}
                    horizon_steps = int(config.get(section, "horizon.steps"))
                    pub_frequency_sec = int(config.get(section, "pub.frequency.sec"))
                    delta_time_sec = int(config.get(section, "delta.time.sec"))
                    mqtt_topic = config.get(section, "mqtt.topic")
                    if horizon_steps is None or pub_frequency_sec is None or \
                            mqtt_topic is None or delta_time_sec is None:
                        logger.info("Topic "+str(section)+" does not have required information.")
                        continue
                    else:
                        mock_params["horizon_steps"] = horizon_steps
                        mock_params["pub_frequency_sec"] = pub_frequency_sec
                        mock_params["delta_time_sec"] = delta_time_sec
                        mock_params["mqtt_topic"] = json.loads(mqtt_topic)

                    mock_source = config.get(section, "mock.source", fallback="random")
                    if mock_source == "file":
                        mock_file_path = config.get(section, "mock.file.path")
                        if mock_file_path is None:
                            logger.error("No mock.file.path specified for topic : "+str(section))
                            continue
                        mock_file_path = os.path.join(os.getcwd(), mock_file_path)
                        logger.info("mock file path = "+str(mock_file_path))
                        mock_params["mock_file_path"] = mock_file_path
                        mock_params["mock_source"] = mock_source
                    elif mock_source == "random":
                        mock_params["mock_source"] = mock_source
                        mock_random_min = float(config.get(section, "mock.random.min", fallback="0"))
                        mock_random_max = float(config.get(section, "mock.random.max", fallback="1"))
                        mock_data_type = config.get(section, "mock.data.type", fallback="float")
                        if mock_random_min > mock_random_max:
                            mock_random_min, mock_random_max = mock_random_max, mock_random_min
                        mock_params["mock_random_min"] = mock_random_min
                        mock_params["mock_random_max"] = mock_random_max
                        mock_params["mock_data_type"] = mock_data_type
                    elif mock_source == "constant":
                        mock_params["mock_source"] = mock_source
                        contant_value = config.get(section, "mock.constant.val", fallback=None)
                        if contant_value is None:
                            logger.error("no constant value specified for "+str(section))
                            continue
                        mock_params["mock_constant"] = contant_value
                        mock_params["horizon_steps"] = 1
                    mgdp = MockGenericDataPublisher(config, mock_params)
                    mgdp.start()
                    self.publishers[section] = mgdp
            except Exception as e:
                logger.error(e)

    def stopMockDataPublisherThreads(self):
        if self.publishers is not None:
            for pub in self.publishers.values():
                pub.Stop()



if __name__ == '__main__':

    config = None
    config_path = "/usr/src/app/mock_data/resources/mockConfig.properties"
    config_path_default = "/usr/src/app/config/mockConfig.properties"
    ConfigUpdater.copy_config(config_path_default, config_path)

    config = configparser.RawConfigParser()
    config.read(config_path)
    log_level = config.get("IO", "log.level", fallback="DEBUG")
    logger = MessageLogger.set_and_get_logger_parent(id="", level=log_level)

    logger.info("Starting mock data generation")
    mockData = MockData(config)
    mockData.startMockDataPublisherThreads(logger)
