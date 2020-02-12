"""
Created on Okt 19 11:53 2018

@author: nishit
"""
import configparser
from config.configUpdater import ConfigUpdater
from connector.Connector import Connector

from utils_intern.messageLogger import MessageLogger

connector_status = {}

if __name__ == '__main__':
    config = None
    config_path = "/usr/src/app/connector/resources/connectorConfig.properties"
    config_path_default = "/usr/src/app/config/connectorConfig.properties"
    config, logger = ConfigUpdater.get_config_and_logger("connector", config_path_default, config_path)

    connector = Connector(config)