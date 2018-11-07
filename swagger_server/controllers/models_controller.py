import connexion
import six
import requests
import shutil

from swagger_server.models.model import Model  # noqa: E501
from swagger_server.models.model_answer import ModelAnswer  # noqa: E501
from swagger_server.models.model_output import ModelOutput
from swagger_server.models.model_url import ModelUrl  # noqa: E501
from swagger_server import util
from flask import json
import os
import logging
import configparser
from os import walk
import re



logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

def getDataJSON(object, key):
    data=json.dumps(object)
    data2=json.loads(data)
    return data2[key]

def getFilePath(dir, file_name):
    # print(os.path.sep)
    # print(os.environ.get("HOME"))
    project_dir = os.path.dirname(os.path.realpath(__file__))
    data_file = os.path.join("/usr/src/app", dir, file_name)
    return data_file

def delete_models(name):  # noqa: E501
    """Deletes the desired model of the framework

     # noqa: E501

    :param name: Name of the model to be deleted
    :type name: str

    :rtype: None
    """
    file_name=str(name)+".py"
    if not "ReferenceModel.py" in file_name:
        logger.debug("This model will be erased: "+str(name))
        file_path= os.path.join("/usr/src/app/optimization/models", file_name)
        try:
            os.remove(file_path)
            # Creating an object of the configuration file in order to change the model.name into the SolverSection
            config = configparser.RawConfigParser()
            config.read(getFilePath("utils", "ConfigFile.properties"))
            model_name = config.get('SolverSection', 'model.name')
            if model_name == name:
                config.set('SolverSection', 'model.name', "ReferenceModel")
                with open(getFilePath("utils", "ConfigFile.properties"), mode='w') as configfile:
                    config.write(configfile)
                config.read(getFilePath("utils", "ConfigFile.properties"))
                logger.info("The model name was changed in the configuration file: " + config['SolverSection']['model.name'])
            answer="OK"
        except Exception as e:
            logger.error(e)
            answer= str(e)
    else:
        answer = "Cannot remove ReferenceModel"
    return answer


def delete_models_all():  # noqa: E501
    """Deletes all models of the framework

     # noqa: E501


    :rtype: None
    """
    f = []
    mypath = "/usr/src/app/optimization/models"
    for (dirpath, dirnames, filenames) in walk(mypath):
        f.extend(filenames)
        break
    try:
        for filenames in f:
            logger.debug("Filenames: " + str(filenames))
            if not "ReferenceModel.py" in filenames:
                file_path = os.path.join("/usr/src/app/optimization/models", filenames)
                logger.debug("File_path: "+file_path)
                os.remove(file_path)
        config = configparser.RawConfigParser()
        config.read(getFilePath("utils", "ConfigFile.properties"))
        model_name = config.get('SolverSection', 'model.name')
        if model_name is not "ReferenceModel":
            config.set('SolverSection', 'model.name', "ReferenceModel")
            with open(getFilePath("utils", "ConfigFile.properties"), mode='w') as configfile:
                config.write(configfile)
            config.read(getFilePath("utils", "ConfigFile.properties"))
            logger.info("The model name was changed in the configuration file: " + config['SolverSection']['model.name'])
        answer = "OK"
    except Exception as e:
        logger.error(e)
        answer= str(e)
    return answer


def get_models_in():  # noqa: E501
    """Fetches all installed models in the framework

     # noqa: E501

    :rtype: None
    """

    f = []
    mypath = "/usr/src/app/optimization/models"
    for (dirpath, dirnames, filenames) in walk(mypath):
        f.extend(filenames)
        logger.debug("Filenames: "+str(f))
        break
    f_new=[]
    for filenames in f:
        filenames = re.sub('.py', '', str(filenames))
        f_new.append(filenames)
    logger.debug("Filenames: " + str(f_new))
    answer=[]

    for i in range(len(f_new)):
        answer.append(ModelOutput(f_new[i]))
    answer=ModelAnswer(answer)

    logger.debug("Answer: " + str(answer))
    return answer


def optimization_model(name, upModel):  # noqa: E501
    """Mathematical model for the optimization solver

     # noqa: E501

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
        string2 = "class Model:\n"
        upModel = connexion.request.get_data(as_text=True)
        upModel = upModel.splitlines()

        classText = string1 + string2

        #Adds an indent at the beginning of each line
        for lines in upModel:
            classText = classText + ('\t')+ lines +('\n')
        logger.debug("Class: " + str(classText) )

        # Saves the class into the /optimization/models
        with open(data_file, mode='w') as localfile:
            localfile.write(classText)

        # Creating an object of the configuration file in order to change the model.name into the SolverSection
        config = configparser.RawConfigParser()
        config.read(getFilePath("utils", "ConfigFile.properties"))
        config.set('SolverSection', 'model.name', name)
        with open(getFilePath("utils", "ConfigFile.properties"), mode='w') as configfile:
            config.write(configfile)
        config.read(getFilePath("utils", "ConfigFile.properties"))
        logger.info("The model name was saved in the configuration file: "+config['SolverSection']['model.name'])
        answer = "OK"

    except Exception as e:
        logger.error(e)
        answer = e
    #upModel=Model.from_dict(connexion.request)
    #data = getDataJSON(upModel, "upModel")
    #print(data)
    return answer




def optimization_model_url(upModelUrl):  # noqa: E501
    """Url for the mathematical model for the optimization solver

     # noqa: E501

    :param upModelUrl: Url of the mathematical model that needs to be added to the optimization framework
    :type upModelUrl: dict | bytes

    :rtype: None
    """

    if connexion.request.is_json:
        logger.info("URL JSON received")
        #print("direct"+str(upModelUrl))
        upModelUrl = ModelUrl.from_dict(connexion.request.get_json())  # noqa: E501

        try:
            url= getDataJSON(upModelUrl,"upModelUrl")
            r=requests.get(url,auth=('garagon', 'initavi2011'), verify=True,stream=True)
            r.raise_for_status() # ensure we notice bad responses
            #print("Headers -->" + str(r.headers))
            #print("Content length "+ str(r.headers.get('Content-length',0)))
            #print("File name " + str(r.headers.get('filename', 0)))
            #print("Este es r.text  ",r.text)
            #print("Este es r.raise_for_status()  ",r.raise_for_status())
            if r.status_code == 200:
                logger.info("File correctly downloaded")

            try:
                with open("/usr/src/app/optimization/models/model_1.py", mode='wb') as localfile:
                    localfile.write(r.content)
                #print(os.path.abspath("model.py"))
            except Exception as e:
                logger.error(e)

        except Exception as e:
            logger.error(e)
    else:
        logger.info("Wrong Content-Type")
    return 'Success'
