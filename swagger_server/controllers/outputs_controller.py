import json
import logging

import connexion
import os
import six

from IO.redisDB import RedisDB
from swagger_server.models.optimization_output import OptimizationOutput  # noqa: E501
from swagger_server.models.output_source import OutputSource  # noqa: E501
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

def delete_mqtt_output(id):  # noqa: E501
    """Deletes the registration output of the framework

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return delete_data(id, "Output.registry.mqtt")

def delete_output(id):  # noqa: E501
    """Deletes the output of the framework

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    redisDB = RedisDB()
    output_keys = redisDB.get_keys_for_pattern("o:" + id + ":*")
    if output_keys is not None:
        for key in output_keys:
            redisDB.remove(key)
    return "success"

def output_source_mqtt(id, Output_Source):  # noqa: E501
    """Creates a new outputs setpoint as ouput

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
    return 'success'


def get_output(id):  # noqa: E501
    """Get ouput of the optimization

     # noqa: E501

    :param id: Name of the registry to be actualized
    :type id: str

    :rtype: OptimizationOutput
    """
    result = {}
    redisDB = RedisDB()
    output_keys = redisDB.get_keys_for_pattern("o:" + id + ":*")
    if output_keys is not None:
        for key in output_keys:
            sub_key = key.split(":")
            topic = sub_key[2]
            index = sub_key[3]
            json_value = redisDB.get(key)
            json_value = json.loads(json_value)
            time = None
            value = 0
            for t, v in json_value.items():
                time = t
                value = v
                break
            if topic not in result.keys():
                result[topic] = {}
            if time is not None:
                if time not in result[topic]:
                    result[topic][time] = {}
                result[topic][time][index] = float(value)
    return OptimizationOutput.from_dict(result)


def get_output_source_mqtt(id):  # noqa: E501
    """Get mqtt output details

     # noqa: E501

    :param id: ID of the output data source to be fetched
    :type id: str

    :rtype: OutputSource
    """
    response = {}
    dir = os.path.join(os.getcwd(), "utils", str(id))
    try:
        if not os.path.exists(dir):
            return "output mqtt not existing"
        else:
            file_registry = os.path.join(dir, "Output.registry.mqtt")
            if os.path.exists(file_registry):
                with open(file_registry, "r") as infile:
                    response = json.load(infile)
            return OutputSource.from_dict(response)
    except Exception as e:
        logger.error("error reading registry " + str(e))
    return "error"