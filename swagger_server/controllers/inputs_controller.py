import json

import connexion
import os
import six

from optimization.utils import Utils
from swagger_server.models.file_output_all import FileOutputAll  # noqa: E501
from swagger_server.models.file_input_source import FileInputSource  # noqa: E501
from swagger_server.models.output_ids_list import OutputIdsList  # noqa: E501

from utils_intern.messageLogger import MessageLogger

logger = MessageLogger.get_logger_parent()
utils = Utils()


def recursively_delete_folder(dir):
    if os.path.exists(dir) and os.path.isdir(dir):
        for file in os.listdir(dir):
            path = os.path.join(dir, file)
            if os.path.isfile(path):
                os.remove(path)
            else:
                recursively_delete_folder(path)
        os.rmdir(dir)


def delete_dataset_registry(id):  # noqa: E501
    """Deletes the loaded data

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    try:
        dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
        if not os.path.exists(dir):
            return "Id not existing"
        else:
            recursively_delete_folder(dir)
            return "success", 200
    except Exception as e:
        logger.error(e)
        return "error", 400


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

            id = utils.create_and_get_ID()
            store_datalists(File_Input_Source, id)
            return "Instance created", 201, {'Location': str(id)}
        except Exception as e:
            logger.error("Invalid data " + str(e))
            return str(e).replace("\"", ""), 400
    else:
        return 'Data is not in json format', 400


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
            File_Input_Source = FileInputSource.from_dict(connexion.request.get_json())  # noqa: E501
            logger.info("This is the dictionary: " + File_Input_Source.to_str())

            File_Input_Source = connexion.request.get_json()
            input_header_validation(File_Input_Source)

            # check if the file exists
            dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
            if not os.path.exists(dir):
                return "Id not existing"
            else:
                # TODO: append information?
                # TODO: delete previous files?
                store_datalists(File_Input_Source, id)
                return "Data source registered", 200
        except Exception as e:
            logger.error("Invalid data " + str(e))
            return str(e).replace("\"", ""), 400
    else:
        return 'Data is not in json format', 400


def store_datalists(File_Input_Source, id):
    dir_data = os.path.join(os.getcwd(), "optimization/resources", str(id), "file")
    if not os.path.exists(dir_data):
        os.makedirs(dir_data)
    # saves the registry into the new folder
    path = os.path.join(os.getcwd(), "optimization/resources", str(id), "Input.registry")
    with open(path, 'w') as outfile:
        json.dump(File_Input_Source, outfile, ensure_ascii=False)
        logger.info("registry/input saved into memory")
    # with open(path, 'r') as file:
    input_all = File_Input_Source
    logger.debug("This is the input " + str(File_Input_Source))
    for header, header_data in input_all.items():
        logger.debug("Header: " + str(header))
        if is_datalist_header(header):
            for name, name_list in header_data.items():
                if name != "meta":
                    logger.debug("Data in " + str(name) + " is " + str(name_list))
                    for i, item in enumerate(name_list):
                        if "datalist" in item.keys():
                            value = item["datalist"]
                            file_name = str(name) + "~" + str(i) + ".txt"
                            path = os.path.join(os.getcwd(), "optimization/resources", str(id), "file",
                                                file_name)
                            logger.debug("Path where the data is stored" + str(path))
                            with open(path, 'w') as outfile:
                                outfile.write(str(value))
                            logger.info("input data saved into memory: " + str(file_name))


def get_data_source_values(id):  # noqa: E501
    """Receives data from the framework

     # noqa: E501

    :param id: ID of the data source
    :type id: str

    :rtype: FileInputSource
    """
    response = {}
    try:
        dir = os.path.join(os.getcwd(), "optimization/resources", str(id))
        if not os.path.exists(dir):
            return "Id not existing"
        else:
            file_registry = os.path.join(dir, "Input.registry")
            if os.path.exists(file_registry):
                with open(file_registry, "r") as infile:
                    response = json.load(infile)
            return FileInputSource.from_dict(response)
            #return response
    except Exception as e:
        logger.error("error reading registry " + str(e))
    return None


def get_all_data_source_values():  # noqa: E501
    """Receives data from the framework

     # noqa: E501


    :rtype: FileOutputAll
    """
    response = {}
    output_id_list = get_all_data_source_ids()
    if output_id_list is not None:
        output_id_list = OutputIdsList.to_dict(output_id_list)
        for id in output_id_list:
            result = get_data_source_values(id)
            if result is not None:
                response[id] = result
    return FileOutputAll.from_dict(response)
    #return response


def get_all_data_source_ids():  # noqa: E501
    """Receives data from the framework

     # noqa: E501


    :rtype: OutputIdsList
    """
    response = []
    try:
        dir = os.path.join(os.getcwd(), "optimization/resources")
        if os.path.exists(dir):
            paths = os.listdir(dir)
            for path in paths:
                if os.path.isdir(os.path.join(dir, path)):
                    response.append(path)
        return OutputIdsList.from_dict(response)
    except Exception as e:
        logger.error("error reading registry " + str(e))
    return None


def input_header_validation(data):
    invalid_headers = []
    for header in data:
        if header not in ["generic", "load", "photovoltaic", "ESS", "grid", "global_control", "EV",
                          "chargers", "uncertainty"]:
            invalid_headers.append(header)
    if len(invalid_headers) > 0:
        raise InvalidHeaderException("Following headers are invalid: " + str(invalid_headers))


def is_datalist_header(header):
    if header in ["generic", "load", "photovoltaic", "ESS", "grid", "global_control"]:
        return True
    else:
        return False


class InvalidHeaderException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)
