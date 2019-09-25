"""
Created on Sep 19 14:02 2019

@author: nishit
"""

import re
from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class EquationParser():

    def __init__(self, config):
        self.config = config
        self.valid_rhs = re.compile(
            '(\s*[a-zA-Z0-9_]+[.][a-zA-Z0-9_]+\s*[+\-]\s*)*(\s*[a-zA-Z0-9_]+[.][a-zA-Z0-9_]+\s*)').search
        self.valid_lhs = re.compile('[a-zA-Z0-9_]+\s*').search
        self.get_var = re.compile('\s*[+\-]\s*').split
        self.get_ops = re.compile('[+\-]').findall
        self.pub_prefix = config.get("IO", "pub.topic.prefix")

    def parse_equation(self, lhs, rhs):
        logger.debug(lhs+" = " +rhs)
        meta_eq = {}
        qos = 1
        if (lhs is not None and self.valid_lhs(lhs) is not None and self.valid_lhs(lhs).span()[1] == len(lhs)) and \
                (rhs is not None and self.valid_rhs(rhs) is not None and self.valid_rhs(rhs).span()[1] == len(rhs)):
            logger.debug("valid eq")
            meta_eq["name"] = lhs
            meta_eq["pub_topic"] = self.pub_prefix + lhs
            ops = self.get_ops(rhs)
            meta_eq["ops"] = ops
            variable_list = self.get_var(rhs)
            meta_eq["variables"] = variable_list
            topic_list = []
            source_list = []
            for v in variable_list:
                source, var = v.split(".")
                topic = self.pub_prefix + source + "/" + var
                topic_list.append((topic, qos))
                source_list.append(source)
            meta_eq["topics"] = topic_list
            meta_eq["sources"] = source_list
        else:
            logger.debug("Invalid equation "+str(lhs)+" = "+str(rhs))
        return meta_eq

    def read_all_equations(self):
        eq_list = []
        if "EQUATIONS" in self.config.sections():
            for lhs, rhs in self.config.items("EQUATIONS"):
                meta_eq = self.parse_equation(lhs, rhs)
                eq_list.append(meta_eq)
        return eq_list