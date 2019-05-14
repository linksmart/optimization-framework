"""
Created on Jan 18 14:16 2019

@author: nishit
"""
import configparser
import logging

import shutil

import os

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class ConfigUpdater:

    @staticmethod
    def copy_config(source_config_path, destination_config_path, config_parser_option=False):
        if not os.path.exists(destination_config_path):
            shutil.copyfile(source_config_path, destination_config_path)
            logger.info("copied config file")
        else:
            source_config = None
            destination_config = None
            try:
                source_config = configparser.RawConfigParser()
                if config_parser_option:
                    source_config.optionxform = str
                source_config.read(source_config_path)
            except Exception as e:
                logger.error(e)

            try:
                destination_config = configparser.RawConfigParser()
                if config_parser_option:
                    destination_config.optionxform = str
                destination_config.read(destination_config_path)
            except Exception as e:
                logger.error(e)

            if source_config is not None and destination_config is not None:
                for section in source_config.sections():
                    section1 = {}
                    for key in source_config[section]:
                        section1[key] = source_config[section][key]
                    if section in destination_config.sections():
                        for key in section1.keys():
                            if key not in destination_config[section] and section != "KEYS":
                                destination_config[section][key] = section1[key]
                                logger.info("updated config with section: " + str(section) + " key: " + str(key))
                    else:
                        destination_config.add_section(section)
                        destination_config[section] = section1.copy()
                        logger.info("updated config with whole section: "+ str(section))
                with open(destination_config_path, "w") as outf:
                    destination_config.write(outf)
