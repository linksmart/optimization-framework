import json
import logging

import connexion
import os
import six

from optimization.utils import Utils

from swagger_server.models.dataset import Dataset  # noqa: E501
from swagger_server import util

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)
utils = Utils()

def getFilePath(dir, file_name):
    data_file = os.path.join("/usr/src/app", dir, file_name)
    return data_file

def get_id():
    uid = "0"
    try:
        path = getFilePath("utils", "registry.id")
        with open(path, 'r') as readfile:
            uid = readfile.readlines()[0]
    except Exception:
        pass
    logger.info("UID is : "+uid)
    return uid

def check_id(id):
    directory = os.path.join(os.getcwd(), "optimization", str(id))
    if os.path.exists(directory):
        return True
    else:
        return False
def delete_parameter_all(id):  # noqa: E501
    """Deletes all loaded data

     # noqa: E501

    :param id: Id of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return 'do some magic!'


def delete_parameter_data(param_name, id):  # noqa: E501
    """Deletes the loaded data

     # noqa: E501

    :param param_name: Name of the data source
    :type param_name: str
    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return 'do some magic!'

def get_data_in(param_name, id, dataset=None):  # noqa: E501
    """Receives data from the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """

    uid = get_id()
    if uid != "0" and uid == id:
        path = getFilePath("optimization", "loadForecast.txt")
        load = []
        try:
            with open(path, 'r') as file:
                load = file.readlines()
        except Exception as e:
            pass
        path = getFilePath("optimization", "pvForecast.txt")
        pv = []
        try:
            with open(path, 'r') as file:
                pv = file.readlines()
        except Exception as e:
            pass
        return "load : "+str(load) + "\npv : "+str(pv)
    else:
        return "Invalid Id"


def load_data_in(param_name, id, dataset=None):  # noqa: E501
    """Submits load data to the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """

    if check_id(id):
        file_name = str(param_name)+".txt"
        path = os.path.join(os.getcwd(), "optimization",str(id),file_name)
        logger.debug("Path where the data is stored" +str(path))
        if connexion.request.is_json:
            dataset = Dataset.from_dict(connexion.request.get_json())  # noqa: E501
        else:
            dataset = connexion.request.get_data(as_text=True)  # noqa: E501
            dataset = dataset.split("\n")
            with open(path, 'w') as outfile:
                outfile.writelines(dataset)
            logger.info("input data saved into memory: "+str(file_name))
        return 'Success'
    else:
        return "Invalid Id"


