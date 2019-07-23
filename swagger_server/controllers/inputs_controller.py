import json

import connexion
import os
import six
from flask import jsonify

from IO.redisDB import RedisDB
from optimization.utils import Utils
from swagger_server.models.file_output_all import FileOutputAll  # noqa: E501
from swagger_server.models.file_input_source import FileInputSource  # noqa: E501
from swagger_server.models.mqtt_input_source import MQTTInputSource  # noqa: E501
from swagger_server.models.mqtt_output_all import MQTTOutputAll  # noqa: E501
from swagger_server.models.output_ids_list import OutputIdsList  # noqa: E501
from swagger_server import util

from utils_intern.messageLogger import MessageLogger
logger = MessageLogger.get_logger_parent()
utils = Utils()


# mqtt flag to be removed after corresponding changes in file api
def store_data(dataset, id, source):
    try:
        dir_data = os.path.join(os.getcwd(), "optimization/resources", str(id), source)
        if not os.path.exists(dir_data):
            os.makedirs(dir_data)
    except Exception as e:
        logger.error("error creating dir " + str(e))
    for header in dataset:
        logger.debug("Headers: " + str(header))
        input = dataset[header]
        logger.debug(header + " present")
        for key in input:
            data = input[key]
            logger.debug("Data in " + str(key) + " is " + str(data))
            if data is not None:
                logger.debug("Data is not None")
                if "meta" in key:
                    file_name = str(header) + "_" + str(key) + ".txt"
                    path = os.path.join(os.getcwd(), "optimization/resources", str(id), source, file_name)
                    logger.debug("Path where the data is stored" + str(path))
                    # dataset = dataset.split(",")
                    if os.path.isfile(path):
                        os.remove(path)

                    with open(path, 'w') as outfile:
                        outfile.writelines(data)
                elif "SoC_Value" in key:
                    file_name = str(key) + ".txt"
                    path = os.path.join(os.getcwd(), "optimization/resources", str(id), source, file_name)
                    logger.debug("Path where the data is stored" + str(path))
                    # dataset = dataset.split(",")
                    if os.path.isfile(path):
                        os.remove(path)
                    with open(path, 'w') as outfile:
                        outfile.write(str(data))
                else:
                    file_name = str(key) + ".txt"
                    path = os.path.join(os.getcwd(), "optimization/resources", str(id), source, file_name)
                    logger.debug("Path where the data is stored" + str(path))
                    # dataset = dataset.split(",")
                    if os.path.isfile(path):
                        os.remove(path)
                    logger.debug("This is the path to open: " + str(path))
                    with open(path, 'w') as outfile:
                        if isinstance(data, list):
                            outfile.writelines(str(i) + '\n' for i in data)
                        else:
                            outfile.writelines(str(data) + '\n')
                    # with open(path, 'w') as outfile:
                    # outfile.write('\n'.join(str(dataset)))
                    # outfile.writelines(str(i) + '\n' for i in data)
            else:
                logger.debug("No data in " + str(key))
    return 1


def delete_data(id, registry_file, source):
    try:
        dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
        if not os.path.exists(dir):
            return "Id not existing"
        else:
            registry = os.path.join(dir, registry_file)
            if os.path.exists(registry):
                os.remove(registry)
            dir_files = os.listdir(dir)
            if dir_files is not None and len(dir_files) == 0:
                os.rmdir(dir)
            path = os.path.join(os.getcwd(), "optimization/resources", str(id), source)
            if os.path.exists(path):
                files = os.listdir(path)
                if files is not None:
                    for file in files:
                        file_path = os.path.join(path, file)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                files = os.listdir(path)
                if files is not None and len(files) == 0:
                    os.rmdir(path)
            path = os.path.join(os.getcwd(), "optimization/resources", str(id))
            if os.path.exists(path):
                dir_files = os.listdir(path)
                if dir_files is not None and len(dir_files) == 0:
                    os.rmdir(path)
            return "success"
    except Exception as e:
        logger.error(e)
        return "error"


def dataset_input_put(id, dataset):  # noqa: E501
    """Submits data to the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str
    :param dataset: Dataset submitted to the framework
    :type dataset: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        try:
            dataset = FileInputSource.from_dict(connexion.request.get_json())  # noqa: E501

            dataset = connexion.request.get_json()
            logger.info("This is the dictionary: " + str(dataset))
            input_header_validation(dataset)
            # check if the file exists
            dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
            if not os.path.exists(dir):
                return "Id not existing"
            else:
                dir_file = os.path.join(dir, "Input.registry.file")
                if os.path.exists(dir_file):
                    # appends information
                    logger.info("Appending information to the file input registry")

                    with open(dir_file, 'r+') as readfile:
                        data = json.load(readfile)
                        for header in dataset:
                            data[header] = dataset[header]
                        readfile.seek(0)
                        json.dump(data, readfile)
                        readfile.truncate()
                    logger.info("data source saved into memory")
                else:
                    # saves the registry into the new folder

                    with open(dir_file, 'w') as outfile:
                        json.dump(dataset, outfile, ensure_ascii=False)
                    logger.info("data source saved into memory")

                store_data(dataset, id, "file")
                return "Data source registered"
        except Exception as e:
            logger.error("Invalid data " + str(e))
            return str(e).replace("\"", "")
    else:
        return 'Data is not in json format'


def delete_data_source_all(id):  # noqa: E501
    """Deletes all loaded data

     # noqa: E501

    :param id: Id of the data source to be deleted
    :type id: str

    :rtype: None
    """
    result_file = delete_data(id, "Input.registry.file", "file")
    result_mqtt = delete_data(id, "Input.registry.mqtt", "mqtt")
    if result_file == "error" or result_mqtt == "error":
        return "error"
    elif result_file == "success" or result_mqtt == "success":
        return "success"
    elif result_file == "Id not existing" and result_mqtt == "Id not existing":
        return "Id not existing"
    else:
        return "error"


def delete_dataset_registry(id):  # noqa: E501
    """Deletes the loaded data

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    result = delete_data(id, "Input.registry.file", "file")
    return result


def delete_mqtt_registry(id):  # noqa: E501
    """Deletes the loaded data

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    result = delete_data(id, "Input.registry.mqtt", "mqtt")
    return result


def dataset_input_source(File_Input_Source):  # noqa: E501
    """Creates a new data source as input

     # noqa: E501

    :param File_Input_Source: Dataset submitted to the framework
    :type File_Input_Source: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        try:
            File_Input_Source = FileInputSource.from_dict(connexion.request.get_json())  # noqa: E501
            logger.info("This is the dictionary: " + File_Input_Source.to_str())

            File_Input_Source = connexion.request.get_json()
            input_header_validation(File_Input_Source)

            try:
                id = utils.create_and_get_ID()
                dir_data = os.path.join(os.getcwd(), "optimization/resources", str(id), "file")
                if not os.path.exists(dir_data):
                    os.makedirs(dir_data)
                dir_data = os.path.join(os.getcwd(), "optimization/resources", str(id))
                if not os.path.exists(dir_data):
                    os.makedirs(dir_data)
            except Exception as e:
                logger.error(e)

            # saves the registry into the new folder
            path = os.path.join(os.getcwd(), "optimization/resources", str(id), "Input.registry.file")
            with open(path, 'w') as outfile:
                json.dump(File_Input_Source, outfile, ensure_ascii=False)
                logger.info("registry/input saved into memory")

            # with open(path, 'r') as file:
            input_all = File_Input_Source
            logger.debug("This is the input " + str(File_Input_Source))

            for header in input_all:
                logger.debug("Headers: " + str(header))
                input = input_all[header]

                if input:
                    logger.debug(header + " present")
                    for key in input:
                        dataset = input[key]
                        logger.debug("Data in " + str(key) + " is " + str(dataset))
                        if dataset is not None:
                            if "meta" in key:
                                file_name = str(header) + "_" + str(key) + ".txt"
                                path = os.path.join(os.getcwd(), "optimization/resources", str(id), "file",
                                                    file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                # dataset = dataset.split(",")
                                with open(path, 'w') as outfile:
                                    outfile.writelines(dataset)
                            elif "SoC_Value" in key:
                                file_name = str(key) + ".txt"
                                path = os.path.join(os.getcwd(), "optimization/resources", str(id), "file",
                                                    file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                # dataset = dataset.split(",")
                                with open(path, 'w') as outfile:
                                    outfile.write(str(dataset))
                            else:
                                file_name = str(key) + ".txt"
                                path = os.path.join(os.getcwd(), "optimization/resources", str(id), "file",
                                                    file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                with open(path, 'w') as outfile:
                                    if isinstance(dataset, list):
                                        outfile.writelines(str(i) + '\n' for i in dataset)
                                    else:
                                        outfile.writelines(str(dataset) + '\n')
                            logger.info("input data saved into memory: " + str(file_name))
                        else:
                            logger.debug("No data in " + str(key))

            return "Instance created", 201, {'Location': str(id)}
        except Exception as e:
            logger.error("Invalid data " + str(e))
            return str(e).replace("\"", "")
    else:
        return 'Data is not in json format'


def get_data_source_values(id):  # noqa: E501
    """Receives data from the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str

    :rtype: FileInputSource
    """
    response = {}
    dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
    try:
        if not os.path.exists(dir):
            return "Id not existing"
        else:
            file_registry = os.path.join(dir, "Input.registry.file")
            if os.path.exists(file_registry):
                with open(file_registry, "r") as infile:
                    response = json.load(infile)
            return FileInputSource.from_dict(response)
    except Exception as e:
        logger.error("error reading registry " + str(e))
    return "error"


def get_mqtt_data_source_values(id):  # noqa: E501
    """Receives data from the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str

    :rtype: MQTTInputSource
    """
    response = {}
    dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
    try:
        if not os.path.exists(dir):
            return "Id not existing"
        else:
            mqtt_registry = os.path.join(dir, "Input.registry.mqtt")
            if os.path.exists(mqtt_registry):
                with open(mqtt_registry, "r") as infile:
                    response = json.load(infile)
            return MQTTInputSource.from_dict(response)
    except Exception as e:
        logger.error("error reading registry " + str(e))
    return None


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
        try:
            dataset = MQTTInputSource.from_dict(connexion.request.get_json())  # noqa: E501
            dataset = connexion.request.get_json()
            logger.info("This is the dictionary: " + str(dataset))
            input_header_validation(dataset)
            # check if the file exists
            dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
            if not os.path.exists(dir):
                return "Id not existing"
            else:
                dir_file = os.path.join(dir, "Input.registry.mqtt")
                if os.path.exists(dir_file):
                    # appends information
                    logger.info("Appending information to the mqtt input registry")

                    with open(dir_file, 'r+') as readfile:
                        data = json.load(readfile)
                        for header in dataset:
                            # logger.debug("Header 1: " + str(header))
                            if not header == "generic":
                                # logger.debug("Not generic")
                                data[header] = dataset[header]
                            elif header == "generic":
                                # logger.debug("Header 1: " + str(header))
                                for key in dataset["generic"]:
                                    # logger.debug("Key: " + str(key))
                                    data["generic"][key] = dataset["generic"][key]

                        readfile.seek(0)
                        logger.debug("Data " + str(data))
                        json.dump(data, readfile)
                        # logger.debug("readfile " + str(readfile))
                        readfile.truncate()
                    logger.info("data source saved into memory")
                else:
                    # saves the registry into the new folder
                    with open(dir_file, 'w') as outfile:
                        json.dump(dataset, outfile, ensure_ascii=False)
                    logger.info("data source saved into memory")

                # store_data(dataset, id, "mqtt")
                return "Data source registered"
        except Exception as e:
            logger.error("Invalid data " + str(e))
            return str(e).replace("\"", "")
    else:
        return 'Data is not in json format'


def mqtt_input_source(MQTT_Input_Source):  # noqa: E501
    """Creates a new mqtt data source as input

     # noqa: E501

    :param MQTT_Input_Source: Data source to be created
    :type MQTT_Input_Source: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        try:
            MQTT_Input_Source = MQTTInputSource.from_dict(connexion.request.get_json())  # noqa: E501
            logger.info("This is the dictionary: " + MQTT_Input_Source.to_str())

            MQTT_Input_Source = connexion.request.get_json()

            input_header_validation(MQTT_Input_Source)
            ####generates an id an makes a directory with the id for the data and for the registry
            try:
                id = utils.create_and_get_ID()
                dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
                if not os.path.exists(dir):
                    os.makedirs(dir)
                dir_data = os.path.join(os.getcwd(), "optimization/resources", str(id), "mqtt")
                if not os.path.exists(dir_data):
                    os.makedirs(dir_data)
            except Exception as e:
                logger.error(e)

            # saves the registry into the new folder
            path = os.path.join(os.getcwd(), "optimization/resources", str(id), "Input.registry.mqtt")
            with open(path, 'w') as outfile:
                json.dump(MQTT_Input_Source, outfile, ensure_ascii=False)
            logger.info("registry/input saved into memory")

            return "Instance created", 201, {'Location': str(id)}
            # return jsonify({'Data-Source-Id': str(id)})
        except Exception as e:
            logger.error("Invalid data " + str(e))
            return str(e).replace("\"", "")
    else:
        return 'Data is not in json format'


def get_all_data_source_values():  # noqa: E501
    """Receives data from the framework

     # noqa: E501


    :rtype: FileOutputAll
    """
    response = {}
    output_id_list = get_all_data_source_ids()
    if output_id_list is not None:
        for id in output_id_list:
            result = get_data_source_values(id)
            if result is not None:
                response[id] = result
    return FileOutputAll.from_dict(response)


def get_all_mqtt_data_source_values():  # noqa: E501
    """Receives all mqtt data from the framework

     # noqa: E501


    :rtype: MQTTOutputAll
    """
    response = {}
    output_id_list = get_all_mqtt_data_source_ids()
    if output_id_list is not None:
        for id in output_id_list:
            result = get_mqtt_data_source_values(id)
            if result is not None:
                response[id] = result
    return MQTTOutputAll.from_dict(response)


def get_all_mqtt_data_source_ids():  # noqa: E501
    """Receives data from the framework

     # noqa: E501


    :rtype: OutputIdsList
    """
    response = []
    dir = os.path.join(os.getcwd(), "optimization/resources")
    try:
        if os.path.exists(dir):
            paths = os.listdir(dir)
            for path in paths:
                if os.path.isdir(os.path.join(dir, path)):
                    if os.path.exists(os.path.join(dir, path, "Input.registry.mqtt")):
                        response.append(path)
        return OutputIdsList.from_dict(response)
    except Exception as e:
        logger.error("error reading registry " + str(e))
    return None


def get_all_data_source_ids():  # noqa: E501
    """Receives data from the framework

     # noqa: E501


    :rtype: OutputIdsList
    """
    response = []
    dir = os.path.join(os.getcwd(), "optimization/resources")
    try:
        if os.path.exists(dir):
            paths = os.listdir(dir)
            for path in paths:
                if os.path.isdir(os.path.join(dir, path)):
                    if os.path.exists(os.path.join(dir, path, "Input.registry.file")):
                        response.append(path)
        return OutputIdsList.from_dict(response)
    except Exception as e:
        logger.error("error reading registry " + str(e))
    return None


def input_header_validation(data):
    invalid_headers = []
    for header in data:
        if header not in ["generic", "load", "photovoltaic", "ESS", "grid", "global_control", "horizons", "EV", "chargers", "uncertainty"]:
            invalid_headers.append(header)
    if len(invalid_headers) > 0:
        raise InvalidHeaderException("Following headers are invalid: " + str(invalid_headers))


class InvalidHeaderException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)
