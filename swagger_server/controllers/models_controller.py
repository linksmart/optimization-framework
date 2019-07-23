import configparser

import connexion
import os

import re
import six

from swagger_server.models import ModelOutput
from swagger_server.models.model import Model  # noqa: E501
from swagger_server.models.model_answer import ModelAnswer  # noqa: E501
from swagger_server import util


from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()

def getFilePath(dir, file_name):
    data_file = os.path.join("/usr/src/app", dir, file_name)
    return data_file

def check_and_remove_from_resources(model_name):
    file_path = os.path.join("/usr/src/app/optimization/resources/models", model_name)
    if os.path.exists(file_path):
        os.remove(file_path)

def delete_models(name):  # noqa: E501
    """Deletes the desired model of the framework

     # noqa: E501

    :param name: Name of the model to be deleted
    :type name: str

    :rtype: None
    """
    file_name = str(name) + ".py"
    if not "ReferenceModel.py" in file_name:
        logger.debug("This model will be erased: " + str(name))
        file_path = os.path.join("/usr/src/app/optimization/models", file_name)
        try:
            os.remove(file_path)
            # remove from resources
            check_and_remove_from_resources(file_name)
            # Creating an object of the configuration file in order to change the model.name into the SolverSection
            config = configparser.RawConfigParser()
            config.read(getFilePath("optimization/resources", "ConfigFile.properties"))
            model_name = config.get('SolverSection', 'model.name')
            if model_name == name:
                config.set('SolverSection', 'model.name', "ReferenceModel")
                with open(getFilePath("optimization/resources", "ConfigFile.properties"), mode='w') as configfile:
                    config.write(configfile)
                config.read(getFilePath("optimization/resources", "ConfigFile.properties"))
                logger.info(
                    "The model name was changed in the configuration file: " + config['SolverSection']['model.name'])
            answer = "OK"
        except Exception as e:
            logger.error(e)
            answer = str(e)
    else:
        answer = "Cannot remove ReferenceModel"
    return answer


def get_models_in():  # noqa: E501
    """Fetches all installed models in the framework

     # noqa: E501


    :rtype: ModelAnswer
    """
    f = []
    mypath = "/usr/src/app/optimization/models"
    for (dirpath, dirnames, filenames) in os.walk(mypath):
        f.extend(filenames)
        logger.debug("Filenames: " + str(f))
        break
    f_new = []
    for filenames in f:
        filenames = re.sub('.py', '', str(filenames))
        f_new.append(filenames)
    logger.debug("Filenames: " + str(f_new))
    answer = []

    for i in range(len(f_new)):
        answer.append(ModelOutput(f_new[i]))
    answer = ModelAnswer(answer)

    logger.debug("Answer: " + str(answer))
    return answer


def optimization_model(name, upModel):  # noqa: E501
    """Mathematical model for the optimization solver

     # noqa: E501

    :param name: Name of the loaded model
    :type name: str
    :param upModel: Mathematical model that needs to be added to the optimization framework
    :type upModel: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        upModel = Model.from_dict(connexion.request.get_json())  # noqa: E501
    try:
        #writes thw data into a file with the given name
        logger.debug("This is the file name: " + name)
        data_file = os.path.join("/usr/src/app/optimization/models", name)+".py"
        string1 = "from pyomo.core import *\n"
        string2 = "from itertools import product\n"
        string3 = "class Model:\n"
        upModel = connexion.request.get_data(as_text=True)
        upModel = upModel.splitlines()

        classText = string1 + string2 + string3

        #Adds an indent at the beginning of each line
        for lines in upModel:
            classText = classText + ('\t')+ lines +('\n')
        logger.debug("Class: " + str(classText) )

        # Saves the class into the /optimization/models
        with open(data_file, mode='w') as localfile:
            localfile.write(classText)

        model_persist_dir_path = "/usr/src/app/optimization/resources/models"
        if not os.path.exists(model_persist_dir_path):
            os.makedirs(model_persist_dir_path)
        data_file_persist = os.path.join("/usr/src/app/optimization/resources/models", name) + ".py"
        # Saves the class into the /optimization/resources/models for persistence
        with open(data_file_persist, mode='w') as localfile:
            localfile.write(classText)

        # Creating an object of the configuration file in order to change the model.name into the SolverSection
        config = configparser.RawConfigParser()
        config.read(getFilePath("optimization/resources", "ConfigFile.properties"))
        config.set('SolverSection', 'model.name', name)
        with open(getFilePath("optimization/resources", "ConfigFile.properties"), mode='w') as configfile:
            config.write(configfile)
        config.read(getFilePath("optimization/resources", "ConfigFile.properties"))
        logger.info("The model name was saved in the configuration file: "+config['SolverSection']['model.name'])
        answer = "OK"

    except Exception as e:
        logger.error(e)
        answer = e
    return answer

def get_optimization_model(name):  # noqa: E501
    """Mathematical model for the optimization solver

     # noqa: E501

    :param name: Name of the loaded model
    :type name: str

    :rtype: Model
    """
    response = []
    data_file = os.path.join("/usr/src/app/optimization/models", name) + ".py"
    flag = False
    if os.path.exists(data_file):
        with open(data_file, mode='r') as localfile:
            model = localfile.readlines()
        for line in model:
            if "class " == line[0:6] and ":" == line.strip()[-1]:
                logger.info(line)
                flag = True
            elif flag:
                line = line.replace("\n", "")
                line = line.replace("\t", "")
                # line = line[4:]
                response.append(line)
        response = "\n".join(response)
        return Model.from_dict(response)
    else:
        return None