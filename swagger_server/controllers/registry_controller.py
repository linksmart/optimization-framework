import connexion
import six

from swagger_server.models.input_source import InputSource  # noqa: E501
from swagger_server.models.output_source import OutputSource  # noqa: E501
from swagger_server import util

from flask import json


def load_source(inputsource):
    """Creates a new data source as input

    :return:
    :param inputsource: Data source to be created
    :type inputsource: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        text = json.loads(json.dumps(inputsource))
        print(text)
        # InputSource = InputSource.from_dict(connexion.request.get_json())
    return 'Created succesfully'


def output_source(OutputSource):  # noqa: E501
    """Creates a new data source as ouput

     # noqa: E501

    :param OutputSource: Output data source to be created
    :type OutputSource: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        OutputSource = OutputSource.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
