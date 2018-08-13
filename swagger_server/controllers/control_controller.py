import connexion
import six
import os, logging, json
from swagger_server.models.output_source import OutputSource  # noqa: E501
from swagger_server.models.path_definition import PathDefinition  # noqa: E501
from swagger_server import util

from optimization.utils import Utils

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)
utils = Utils()


def delete_data(id, registry_file):
    try:
        path = os.path.join(os.getcwd(), "utils", str(id), registry_file)
        logger.info("file to be deleted is "+str(path))
        if not os.path.exists(path):
            return "Id not existing"
        else:
            os.remove(path)
            return "success"
    except Exception as e:
        logger.error(e)
        return "error"

def delete_file_output(id):  # noqa: E501
    """Deletes the registration output of the framework

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    """also need to delete output files"""
    return delete_data(id, "Output.registry.file")


def delete_mqtt_output(id):  # noqa: E501
    """Deletes the registration output of the framework

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return delete_data(id, "Output.registry.mqtt")


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
        dataset = connexion.request.get_json()
        logger.info("This is the dictionary: " + Output_Source.to_str())
        try:
            dir = os.path.join(os.getcwd(), "utils", str(id))
            if not os.path.exists(dir):
                os.makedirs(dir)
        except Exception as e:
            logger.error(e)

        # saves the registry into the new folder
        path = os.path.join(os.getcwd(), "utils", str(id), "Output.registry.mqtt")
        with open(path, 'w') as outfile:
            json.dump(dataset, outfile, ensure_ascii=False)
        logger.info("control output saved into memory")
    return 'do some magic!'


