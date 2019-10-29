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
    ConfigUpdater.copy_config(config_path_default, config_path, True)

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_path)
    log_level = config.get("IO", "log.level", fallback="DEBUG")
    logger = MessageLogger.set_and_get_logger_parent(id="", level=log_level)

    connector = Connector(config)