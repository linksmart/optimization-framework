"""
Created on Sep 19 14:02 2019

@author: nishit
"""
import json
import re
from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class EquationParser():

    def __init__(self, config):
        self.config = config
        self.valid_lhs = re.compile('[a-zA-Z0-9_]+\s*').search
        self.valid_variable = re.compile('[a-zA-Z][a-zA-Z0-9_]*[.][a-zA-Z0-9_]+').search
        self.get_var = re.compile('\s*[+\-*/()]\s*').split
        self.get_ops = re.compile('[+\-]').findall
        self.pub_prefix = "con/opt/"#config.get("IO", "pub.topic.prefix")
        self.valid_dtype = ["float", "int"]

    def valid(self, func, string):
        return string is not None and len(string) > 0 and func(string) is not None and func(string).span()[1] == len(
            string)

    def parse_equation(self, lhs, rhs_dict):
        rhs_dict = json.loads(rhs_dict)
        rhs = rhs_dict["eq"]
        logger.debug(lhs+" = " +rhs)
        meta_eq = {}
        qos = 1
        if self.valid(self.valid_lhs, lhs):
            logger.debug("valid eq")
            if "min" in rhs_dict.keys():
                min = float(rhs_dict["min"])
                meta_eq["min"] = min
            if "max" in rhs_dict.keys():
                max = float(rhs_dict["max"])
                meta_eq["max"] = max
            dtype = "float"
            if "dtype" in rhs_dict.keys():
                dtype = rhs_dict["dtype"]
                if dtype not in self.valid_dtype:
                    dtype = "float"
            meta_eq["dtype"] = dtype
            meta_eq["name"] = lhs
            meta_eq["pub_topic"] = self.pub_prefix + lhs
            variable_dict = {}
            for var in self.get_var(rhs):
                if self.valid(self.valid_variable, var):
                    if var not in variable_dict.keys():
                        variable_dict[var] = "x" + str(len(variable_dict))
            meta_eq["variables"] = variable_dict
            topic_list = []
            source_list = []
            for v in variable_dict.keys():
                source, var = v.split(".")
                topic = self.pub_prefix + source + "/" + var
                topic_list.append((topic, qos))
                source_list.append(source)
            meta_eq["topics"] = topic_list
            meta_eq["sources"] = source_list
            for var, rep in variable_dict.items():
                rhs = rhs.replace(var, rep)
            logger.debug("equation = "+str(rhs))
            meta_eq["eq"] = compile(rhs, filename="equation", mode="eval")
        else:
            logger.debug("Invalid equation "+str(lhs)+" = "+str(rhs))
        return meta_eq

    def read_all_equations(self):
        eq_list = []
        if "EQUATIONS" in self.config.sections():
            for lhs, rhs_dict in self.config.items("EQUATIONS"):
                meta_eq = self.parse_equation(lhs, rhs_dict)
                eq_list.append(meta_eq)
        return eq_list