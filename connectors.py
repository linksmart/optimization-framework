"""
Created on Okt 19 11:53 2018

@author: nishit
"""
import configparser
import json
import logging

import os

from connector.Connector import Connector

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

if __name__ == '__main__':
    config = None
    try:
        config = configparser.ConfigParser()
        config.optionxform = str
        data_file = os.path.join("/usr/src/app", "connector/resources", "connectorConfig.properties")
        config.read(data_file)
    except Exception as e:
        logger.error(e)

    rec_params = config.get("IO", "con.topic")
    rec_params = json.loads(rec_params)

    connector = Connector(rec_params, config)