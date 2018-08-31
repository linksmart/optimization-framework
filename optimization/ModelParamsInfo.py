"""
Created on Aug 31 12:02 2018

@author: nishit
"""
import logging
import os

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

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
        return f

    @staticmethod
    def get_model_param(model_name):
        models = ModelParamsInfo.get_models()
        lines = []
        var_map = {}
        for model in models:
            if model_name in model:
                with open(model, "r") as infile:
                    lines = infile.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith("model.") and "==" not in line:
                pos_of_eq = line.find("=")
                if pos_of_eq > 0:
                    pos_of_model = line.find("model.")
                    if -1 < pos_of_model < pos_of_eq:
                        var_name = line[pos_of_model+len("model."): pos_of_eq].strip()
                        type_name, indexing = ModelParamsInfo.pos_and_type_of_var(line, pos_of_eq)
                        if type_name is not None:
                            var_map[var_name] = {"type":type_name, "indexing":indexing}
        return var_map

    @staticmethod
    def pos_and_type_of_var(line, pos_of_equal):
        types = ["Set", "Param", "Var"]
        for type in types:
            if type in line:
                pos_of_type = line.find(type+"(")
                if pos_of_type > pos_of_equal:
                    type_name = type
                    num_of_args = 0
                    pos_of_start_bracket = line.find("(", pos_of_type+1)
                    pos_of_end_bracket = line.find(")", pos_of_type+1)
                    if pos_of_start_bracket + 1 == pos_of_end_bracket:
                        num_of_args = 0
                    else:
                        num_of_args = 1
                        pos_of_comma = line.find(",")
                        while pos_of_comma != -1:
                            num_of_args += 1
                            pos_of_comma = line.find(",", pos_of_comma+1)
                    if num_of_args > 1:
                        return type_name, "index"
                    else:
                        return type_name, "None"
        return None, None

