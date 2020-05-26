"""
Created on Aug 31 12:02 2018

@author: nishit
"""
import os

from optimization.ModelException import InvalidModelException
from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

class ModelParamsInfo:

    @staticmethod
    def get_models():
        f = []
        dir = os.path.dirname(os.path.realpath(__file__))
        mypath = os.path.join(dir, "models")
        if os.path.exists(mypath):
            for file in os.listdir(mypath):
                file_path = os.path.join(mypath, file)
                if os.path.isfile(file_path) and file[len(file)-3:] == ".py":
                    f.append(file_path)
        return (f, mypath)

    @staticmethod
    def pos_and_type_of_var(line, pos_of_equal):
        types = ["Set", "Param"]
        for type in types:
            if type in line:
                pos_of_type = line.find(type + "(")
                if pos_of_type > pos_of_equal:
                    type_name = type
                    set_names = []
                    pos_of_start_bracket = line.find("(", pos_of_type + 1)
                    pos_of_end_bracket = line.find(")", pos_of_type + 1)
                    if pos_of_start_bracket + 1 != pos_of_end_bracket:
                        start = pos_of_start_bracket + 1
                        pos_of_comma = line.find(",")
                        while pos_of_comma != -1:
                            set_name = line[start: pos_of_comma].strip()
                            if "=" not in set_name and "model." in set_name:
                                set_names.append(set_name.replace("model.", ""))
                            start = pos_of_comma + 1
                            pos_of_comma = line.find(",", pos_of_comma + 1)
                    return type_name, set_names
        return (None, None)

    @staticmethod
    def get_model_param(model_name):
        models, basepath = ModelParamsInfo.get_models()
        lines = []
        var_map = {}
        param_key_list = []
        for model in models:
            if os.path.join(basepath, model_name + ".py") == model:
                with open(model, "r") as infile:
                    lines = infile.readlines()
                break
        for line in lines:
            line = line.strip()
            if line.startswith("model.") and "==" not in line:
                pos_of_eq = line.find("=")
                if pos_of_eq > 0:
                    pos_of_model = line.find("model.")
                    if -1 < pos_of_model < pos_of_eq:
                        var_name = line[pos_of_model + len("model."): pos_of_eq].strip()
                        type_name, indexing = ModelParamsInfo.pos_and_type_of_var(line, pos_of_eq)
                        if type_name is not None:
                            if len(indexing) > 2:
                                raise InvalidModelException("model component "+var_name+
                                                            " has more indices than 2 "+str(indexing))
                            var_map[var_name] = {"type": type_name, "indexing": indexing}
                            if type_name == "Param":
                                param_key_list.append(var_name)
        return (var_map, param_key_list)
