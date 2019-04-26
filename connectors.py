"""
Created on Okt 19 11:53 2018

@author: nishit
"""
import configparser
import json
import logging

import os

import shutil

from config.configUpdater import ConfigUpdater
from connector.Connector import Connector
from connector.apiConnectorFactory import ApiConnectorFactory

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

if __name__ == '__main__':
    config = None
    config_path = "/usr/src/app/connector/resources/connectorConfig.properties"
    config_path_default = "/usr/src/app/config/connectorConfig.properties"
    ConfigUpdater.copy_config(config_path_default, config_path, True)

    try:
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(config_path)
    except Exception as e:
        logger.error(e)

    workers = config.getint("IO", "number.of.workers", fallback=2)

    try:
        connector_list = []
        for section in config.sections():
            if (section.startswith('HOUSE')):
                logger.info("House: " + section)
                rec_url = config.get(section, "con.url", fallback=None)
                if rec_url:
                    connector = ApiConnectorFactory.get_api_connector(section, rec_url, config, section)
                    connector_list.append(connector)
                else:
                    rec_params = config.get(section, "con.topic", fallback=None)
                    if rec_params:
                        rec_params = json.loads(rec_params)
                        connector = Connector(rec_params, workers, config, section)
                        connector_list.append(connector)
    except Exception as e:
        logger.error(e)