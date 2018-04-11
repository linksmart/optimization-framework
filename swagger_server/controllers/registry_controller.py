import connexion
import six

from swagger_server.models.input_source import InputSource  # noqa: E501
from swagger_server.models.output_source import OutputSource  # noqa: E501
from swagger_server import util


def load_source(InputSource):  # noqa: E501
    """Creates a new data source as input

     # noqa: E501

    :param InputSource: Data source to be created
    :type InputSource: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        InputSource = InputSource.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


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
