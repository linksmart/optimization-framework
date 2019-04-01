"""
Created on Apr 01 14:00 2019

@author: nishit
"""
import logging


class MessageLogger:

    @staticmethod
    def get_logger(file, id=""):
        logger = logging.getLogger(file)
        syslog = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(id)s %(name)s: %(message)s')
        syslog.setFormatter(formatter)
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            logger.addHandler(syslog)
        extra = {"id": id}
        logger = logging.LoggerAdapter(logger, extra)
        return logger