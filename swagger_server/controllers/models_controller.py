import connexion
import six
import requests
import shutil

from swagger_server.models.model import Model  # noqa: E501
from swagger_server.models.model_url import ModelUrl  # noqa: E501
from swagger_server import util
from flask import json
import os
import logging
import configparser



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
        print("This is the file name: " + name)
        data_file = os.path.join("/usr/src/app/optimization/models", name)+".py"
        #print("File name: "+data_file)
        with open(data_file, mode='wb') as localfile:
            localfile.write(upModel)

        # Creating an object of the configuration file in order to change the model.name into the SolverSection
        config = configparser.RawConfigParser()
        config.read(getFilePath("utils", "ConfigFile.properties"))
        config.set('SolverSection', 'model.name', name)
        with open(getFilePath("utils", "ConfigFile.properties"), mode='w') as configfile:
            config.write(configfile)
        config.read(getFilePath("utils", "ConfigFile.properties"))
        logger.info("Se cambio el nombre?: "+config['SolverSection']['model.name'])
        #print("Config solver name: "+config.get("SolverSection", "model.name"))


    except Exception as e:
        logger.error(e)
    #upModel=Model.from_dict(connexion.request)
    #data = getDataJSON(upModel, "upModel")
    #print(data)
    return 'do some magic 1!'




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
    return 'do some magic 2'
