"""
Created on Apr 01 14:00 2019

@author: nishit
"""
import logging


class MessageLogger:

    @staticmethod
    def set_and_get_logger_parent(id="", level="INFO"):
        if id is None:
            id = ""
        parent = "ofw"
        logger = logging.getLogger(parent)
        syslog = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s [%(id)s] %(name)s: %(message)s')
        syslog.setFormatter(formatter)
        log_level = MessageLogger.get_log_level(level)
        logger.setLevel(log_level)
        logger.propagate = False
        if not logger.handlers:
            logger.addHandler(syslog)
        extra = {"id": id}
        logger = logging.LoggerAdapter(logger, extra)
        # TODO: for changing
        return logger

    @staticmethod
    def get_log_level(level):
        level = level.upper()
        switcher = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        return switcher.get(level, logging.DEBUG)

    @staticmethod
    def get_logger(name, id):
        parent = "ofw"
        name = parent+"."+str(name)
        logger = logging.getLogger(name)
        if id is None:
            id = ""
        extra = {"id": id}
        logger = logging.LoggerAdapter(logger, extra)
        return logger

    @staticmethod
    def get_logger_parent():
        parent = "ofw"
        logger = logging.getLogger(parent)
        extra = {"id": ""}
        logger = logging.LoggerAdapter(logger, extra)
        return logger
