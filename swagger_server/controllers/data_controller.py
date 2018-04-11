import connexion
import six

from swagger_server.models.dataset import Dataset  # noqa: E501
from swagger_server import util


def data_in(id, dataset=None):  # noqa: E501
    """Submits data to the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: int
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        dataset = Dataset.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def get_data_in(id, dataset=None):  # noqa: E501
    """Receives data from the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: int
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        dataset = Dataset.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
