"""
Created on Okt 19 11:53 2018

@author: nishit
"""
import configparser
import json

import os

import shutil

from config.configUpdater import ConfigUpdater
from connector.Connector import Connector
from connector.apiConnectorFactory import ApiConnectorFactory
from connector.equationConnector import EquationConnector
from connector.equationParser import EquationParser

from utils_intern.messageLogger import MessageLogger

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

    workers = config.getint("IO", "number.of.workers", fallback=2)
    equation_parser = EquationParser(config)
    equation_list = equation_parser.read_all_equations()
    connector_list = []
    active_sources = []
    for section in config.sections():
        try:
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
                        active_sources.append(section)
        except Exception as e:
            logger.error(e)

    logger.debug("#########"+str(equation_list))
    logger.debug("#####"+str(active_sources))
    for meta_eq in equation_list:
        try:
            all_sources_active = True
            for source in meta_eq["sources"]:
                logger.debug("### sour "+str(source))
                if source not in active_sources:
                    all_sources_active = False
                    logger.debug("##### all sources not active for eq")
                    break
            if all_sources_active:
                connector = EquationConnector(meta_eq, config)
                connector_list.append(connector)
        except Exception as e:
            logger.error(e)