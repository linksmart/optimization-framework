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

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

def getDataJSON(object, key):
    data=json.dumps(object)
    data2=json.loads(data)
    return data2[key]

def optimization_model(upModel):  # noqa: E501
    """Mathematical model for the optimization solver

     # noqa: E501

    :param upModel: Mathematical model that needs to be added to the optimization framework
    :type upModel: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        upModel = Model.from_dict(connexion.request.get_json())  # noqa: E501

    try:
        with open("/usr/src/app/optimization/models/model_2.py", mode='wb') as localfile:
            localfile.write(upModel)
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
