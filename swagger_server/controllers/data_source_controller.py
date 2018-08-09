import connexion
import six
import logging, os
from flask import json

from optimization.utils import Utils
from swagger_server.models.file_input_source import FileInputSource  # noqa: E501
from swagger_server.models.mqtt_input_source import MQTTInputSource  # noqa: E501
from swagger_server.controllers.command_controller import CommandController
from swagger_server import util

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)
utils = Utils()

def delete_data_source_all(id):  # noqa: E501
    """Deletes all loaded data

     # noqa: E501

    :param id: Id of the data source to be deleted
    :type id: str

    :rtype: None
    """
    return 'do some magic!'


def delete_file_registry(id):  # noqa: E501
    """Deletes the loaded data

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return 'do some magic!'


def delete_mqtt_registry(id):  # noqa: E501
    """Deletes the loaded data

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return 'do some magic!'

def file_input_put(id, dataset):  # noqa: E501
    """Submits data to the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        dataset = FileInputSource.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'

def file_input_source(File_Input_Source):  # noqa: E501
    """Creates a new data source as input

     # noqa: E501

    :param File_Input_Source: Dataset submitted to the framework
    :type File_Input_Source: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        File_Input_Source = FileInputSource.from_dict(connexion.request.get_json())  # noqa: E501

        try:
            id = utils.create_and_get_ID()
            dir_data = os.path.join(os.getcwd(), "optimization", str(id))
            if not os.path.exists(dir_data):
                os.makedirs(dir_data)
            dir_data = os.path.join(os.getcwd(), "utils", str(id))
            if not os.path.exists(dir_data):
                os.makedirs(dir_data)
        except Exception as e:
            logger.error(e)

        input_all = File_Input_Source.to_dict()
        for header in input_all:
            logger.debug("Headers: "+ str(header))
            input = input_all[header]
            if input:
                logger.debug(header + " present")
                for key in input:
                    dataset = input[key]
                    logger.debug("Data in "+str(key)+" is " + str(dataset))
                    if dataset is not None:
                        if not "generic" in str(header):
                            logger.debug("Type of "+str(key)+str(type(key)))
                            logger.debug("Type of dataset" + str(type(dataset)))
                            #logger.debug("Size of dataset" + str(len(dataset)))
                            if "soc_value" in str(key):
                                logger.debug("soc_value")
                            elif "SoC_Value" in str(key):
                                logger.debug("SoC_Value")
                            elif "so_c_value" in str(key):
                                logger.debug("so_c_value")
                            else:
                                logger.debug("key: "+str(key))

                            if "meta" in key:
                                file_name = str(header) + "_" + str(key) + ".txt"
                                path = os.path.join(os.getcwd(), "optimization", str(id), file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                # dataset = dataset.split(",")
                                with open(path, 'w') as outfile:
                                    outfile.writelines(dataset)
                            elif "so_c_value" in key:
                                file_name = str(key) + ".txt"
                                path = os.path.join(os.getcwd(), "optimization", str(id), file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                # dataset = dataset.split(",")
                                with open(path, 'w') as outfile:
                                    outfile.write(str(dataset))
                            else:
                                file_name = str(key) + ".txt"
                                path = os.path.join(os.getcwd(), "optimization", str(id), file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                # dataset = dataset.split(",")
                                with open(path, 'w') as outfile:
                                    #outfile.write('\n'.join(str(dataset)))
                                    outfile.writelines(str(i) + '\n' for i in dataset)


                            logger.info("input data saved into memory: " + str(file_name))
                        else:
                            if "name" in str(key):
                                file_name = str(dataset)+".txt"
                            else:
                                path = os.path.join(os.getcwd(), "optimization", str(id), file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                # dataset = dataset.split(",")
                                with open(path, 'w') as outfile:
                                    outfile.writelines(str(dataset))
                                logger.info("input data saved into memory: " + str(file_name))
                    else:
                        logger.debug("No data in "+str(key))

        # saves the registry into the new folder
        path = os.path.join(os.getcwd(), "utils", str(id), "Input.registry")
        with open(path, 'w') as outfile:
            json.dump(File_Input_Source, outfile, ensure_ascii=False)
            logger.info("registry/input saved into memory")


        return 'Data source Id: ' + str(id)
    else:
        return 'Data is not in json format'



def get_data_source_values(param_name, id):  # noqa: E501
    """Receives data from the framework

     # noqa: E501

    :param param_name: Name of the parameter of the optimization model
    :type param_name: str
    :param id: ID of the data source
    :type id: str

    :rtype: None
    """
    return 'do some magic!'

def mqtt_input_put(id, dataset):  # noqa: E501
    """Submits data to the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        dataset = MQTTInputSource.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def mqtt_input_source(MQTT_Input_Source):  # noqa: E501
    """Creates a new mqtt data source as input

     # noqa: E501

    :param MQTT_Input_Source: Data source to be created
    :type MQTT_Input_Source: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        MQTT_Input_Source = MQTTInputSource.from_dict(connexion.request.get_json())  # noqa: E501
        logger.info("This is the dictionary: " + MQTT_Input_Source.to_str())


        # ToDo Error checklist
        # if file is true then mqtt is false
        # limitation of qos
        # topic just base name
        # check with the model
        """try:
            check = error_check_input(Input_Source)
            if check != 0:
                message = "Definition Error " + check
                logger.error(message)
                return message
        except Exception as e:
            logger.error(e)"""

        ####generates an id an makes a directory with the id for the data and for the registry
        try:
            id = utils.create_and_get_ID()
            dir = os.path.join(os.getcwd(), "utils", str(id))
            if not os.path.exists(dir):
                os.makedirs(dir)
            dir_data = os.path.join(os.getcwd(), "optimization", str(id))
            if not os.path.exists(dir_data):
                os.makedirs(dir_data)
        except Exception as e:
            logger.error(e)

        # saves the registry into the new folder
        path = os.path.join(os.getcwd(), "utils", str(id), "Input.registry")
        with open(path, 'w') as outfile:
            json.dump(MQTT_Input_Source, outfile, ensure_ascii=False)
        logger.info("registry/input saved into memory")

        return 'Data source Id: ' + str(id)

    else:
        return 'Data is not in json format'
