"""
Created on Okt 19 11:53 2018

@author: nishit
"""
import configparser
import json
import logging

import os

import shutil

from connector.Connector import Connector

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

if __name__ == '__main__':
    config = None
    config_path = "/usr/src/app/connector/resources/connectorConfig.properties"
    if not os.path.exists(config_path):
        shutil.copyfile("/usr/src/app/config/connectorConfig.properties", config_path)
    try:
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(config_path)
    except Exception as e:
        logger.error(e)

    try:
        connector_list = []
        for section in config.sections():
            if (section.startswith('HOUSE')):
                logger.info("House: " + section)
                rec_params = config.get(section, "con.topic")
                rec_params = json.loads(rec_params)
                connector = Connector(rec_params, config, section)
                connector_list.append(connector)
    except Exception as e:
        logger.error(e)