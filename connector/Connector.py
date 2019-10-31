"""
Created on Okt 29 13:15 2019

@author: nishit
"""
import json
import threading

import time

from connector.apiConnectorFactory import ApiConnectorFactory
from connector.equationConnector import EquationConnector
from connector.equationParser import EquationParser
from connector.parserConnector import ParserConnector
from utils_intern.messageLogger import MessageLogger

logger = MessageLogger.get_logger_parent()

class Connector:

    def __init__(self, config):
        self.config = config
        self.workers = config.getint("IO", "number.of.workers", fallback=2)
        self.connector_list = []
        self.active_sources = {}
        for section in config.sections():
            if section.startswith('HOUSE'):
                self.active_sources[section] = False
                threading.Thread(target=self.start_connector, args=(section,)).start()
        equation_parser = EquationParser(config)
        equation_list = equation_parser.read_all_equations()
        logger.debug("######### Equation list = " + str(equation_list))
        time.sleep(120)
        for meta_eq in equation_list:
            threading.Thread(target=self.start_equation, args=(meta_eq,)).start()

    def start_connector(self, section):
        repeat = 0
        wait_time = 600
        while not self.active_sources[section]:
            if repeat > 0:
                wait_time *= 2
                if wait_time > 6*60*60:
                    wait_time = 6*60*60
                logger.info("re-trying connection after "+str(wait_time)+" sec for house "+str(section))
                time.sleep(wait_time)
            try:
                logger.info("House: " + section)
                rec_url = self.config.get(section, "con.url", fallback=None)
                rec_params = self.config.get(section, "con.topic", fallback=None)
                if rec_url:
                    connector = ApiConnectorFactory.get_api_connector(section, rec_url, self.config, section)
                    self.connector_list.append(connector)
                    self.active_sources[section] = True
                elif rec_params:
                    rec_params = json.loads(rec_params)
                    connector = ParserConnector(rec_params, self.workers, self.config, section)
                    self.connector_list.append(connector)
                    self.active_sources[section] = True
                else:
                    self.active_sources[section] = False
            except Exception as e:
                logger.error(e)
            repeat += 1

    def start_equation(self, meta_eq):
        repeat = 0
        wait_time = 60
        connector_started = False
        all_sources_deaclred = True
        while not connector_started and all_sources_deaclred:
            if repeat > 0:
                wait_time *= 2
                if wait_time > 60*60:
                    wait_time = 60*60
                logger.info("re-trying connection after "+str(wait_time)+" sec for eq "+str(meta_eq["name"]))
                time.sleep(wait_time)
            try:
                all_sources_active = True
                for source in meta_eq["sources"]:
                    logger.debug("### sour " + str(source))
                    if source not in self.active_sources.keys():
                        all_sources_deaclred = False
                        logger.debug("##### house "+str(source)+" data not declared in config")
                        break
                    elif not self.active_sources[source]:
                        all_sources_active = False
                        logger.debug("##### house " + str(source) + " not active yet")
                if all_sources_deaclred and all_sources_active:
                    connector = EquationConnector(meta_eq, self.config)
                    self.connector_list.append(connector)
            except Exception as e:
                logger.error(e)
            repeat += 1