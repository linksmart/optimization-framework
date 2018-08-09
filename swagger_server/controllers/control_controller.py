import connexion
import six

from swagger_server.models.output_source import OutputSource  # noqa: E501
from swagger_server.models.path_definition import PathDefinition  # noqa: E501
from swagger_server import util


def delete_file_output(id):  # noqa: E501
    """Deletes the registration output of the framework

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return 'do some magic!'


def delete_mqtt_output(id):  # noqa: E501
    """Deletes the registration output of the framework

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return 'do some magic!'


def output_source_file(id, Output_Source):  # noqa: E501
    """Creates a new data source as ouput

     # noqa: E501

    :param id: Name of the registry to be actualized
    :type id: str
    :param Output_Source: Output data source to be created
    :type Output_Source: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        Output_Source = PathDefinition.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def output_source_mqtt(id, Output_Source):  # noqa: E501
    """Creates a new control setpoint as ouput

     # noqa: E501

    :param id: Name of the data source to be actualized
    :type id: str
    :param Output_Source: Output data source to be created
    :type Output_Source: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        Output_Source = OutputSource.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
