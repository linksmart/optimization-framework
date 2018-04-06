import connexion
import six

from swagger_server.models.datainput import Datainput  # noqa: E501
from swagger_server import util


def change_input_channel_by_id(id, name=None):  # noqa: E501
    """Change the parameters of a data source by id

     # noqa: E501

    :param id: Setting of the input channels for the optimization framework
    :type id: int
    :param name: Updated name of the channel
    :type name: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        name = Datainput.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def set_input_channel(setInputSource):  # noqa: E501
    """Creates a new data source as input

     # noqa: E501

    :param setInputSource: Data source to be created
    :type setInputSource: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        setInputSource = Datainput.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
