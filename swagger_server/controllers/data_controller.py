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


def getFilePath(dir, file_name):
    data_file = os.path.join("/usr/src/app", dir, file_name)
    return data_file

def get_data_in(id, dataset=None):  # noqa: E501
    """Receives data from the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """
    if id == str(Utils.get_ID()):
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


def load_data_in(id, dataset=None):  # noqa: E501
    """Submits load data to the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """
    if id == str(Utils.get_ID()):
        path = getFilePath("optimization", "loadForecast.txt")
        if connexion.request.is_json:
            dataset = Dataset.from_dict(connexion.request.get_json())  # noqa: E501
        else:
            dataset = connexion.request.get_data(as_text=True)  # noqa: E501
            dataset = dataset.split("\n")
            with open(path, 'w') as outfile:
                outfile.writelines(dataset)
            logger.info("input data saved into memory")
        return 'Success'
    else:
        return "Invalid Id"


def pv_data_in(id, dataset=None):  # noqa: E501
    """Submits load data to the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """
    if id == str(Utils.get_ID()):
        path = getFilePath("optimization", "pvForecast.txt")
        if connexion.request.is_json:
            dataset = Dataset.from_dict(connexion.request.get_json())  # noqa: E501
        else:
            dataset = connexion.request.get_data(as_text=True)  # noqa: E501
            dataset = dataset.split("\n")
            with open(path, 'w') as outfile:
                outfile.writelines(dataset)
            logger.info("input data saved into memory")
        return 'Success'
    else:
        return "Invalid Id"
