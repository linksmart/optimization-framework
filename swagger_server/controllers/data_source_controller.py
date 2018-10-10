import connexion
import six
import logging, os
from flask import json
from flask import jsonify
from os.path import isfile, join

from optimization.utils import Utils
from swagger_server.models.file_input_source import FileInputSource  # noqa: E501
from swagger_server.models.mqtt_input_source import MQTTInputSource  # noqa: E501
from swagger_server import util

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)
utils = Utils()

# mqtt flag to be removed after corresponding changes in file api
def store_data(dataset, id,source):
    try:
        dir_data = os.path.join(os.getcwd(), "optimization", str(id), source)
        if not os.path.exists(dir_data):
            os.makedirs(dir_data)
    except Exception as e:
        logger.error("error creating dir "+str(e))
    for header in dataset:
        logger.debug("Headers: " + str(header))
        input = dataset[header]
        logger.debug(header + " present")
        if header == "generic":
            for item in input:
                for key in item:
                    data = item[key]
                    logger.debug("Data in " + str(key) + " is " + str(data))
                    if data is not None:
                        logger.debug("Data is not None")
                        logger.debug("generic")
                        if "generic_name" or "file " in key:
                            name = item["name"]
                            file_name = str(name) + ".txt"
                            logger.debug("This is the file name for generic: " + str(file_name))
                            path = os.path.join(os.getcwd(), "optimization", str(id), source, file_name)
                            logger.debug("Path where the data is stored" + str(path))
                            # dataset = dataset.split(",")
                            if os.path.isfile(path):
                                logger.debug("Path exists")
                                os.remove(path)
                                logger.debug("File erased")

                            path = os.path.join(os.getcwd(), "optimization", str(id), source, file_name)
                            logger.debug("Path where the data is stored" + str(path))
                            with open(path, 'w') as outfile:
                                outfile.writelines(str(i) + '\n' for i in data)
                            logger.info("input data saved into memory: " + str(file_name))
                    else:
                        logger.debug("No data in " + str(key))
        else:
            for key in input:
                data = input[key]
                logger.debug("Data in " + str(key) + " is " + str(data))
                if data is not None:
                    logger.debug("Data is not None")
                    if "meta" in key:
                        file_name = str(header) + "_" + str(key) + ".txt"
                        path = os.path.join(os.getcwd(), "optimization", str(id),source, file_name)
                        logger.debug("Path where the data is stored" + str(path))
                        # dataset = dataset.split(",")
                        if os.path.isfile(path):
                            os.remove(path)

                        with open(path, 'w') as outfile:
                            outfile.writelines(data)
                    elif "SoC_Value" in key:
                        file_name = str(key) + ".txt"
                        path = os.path.join(os.getcwd(), "optimization", str(id), source, file_name)
                        logger.debug("Path where the data is stored" + str(path))
                        # dataset = dataset.split(",")
                        if os.path.isfile(path):
                            os.remove(path)
                        with open(path, 'w') as outfile:
                            outfile.write(str(data))
                    else:
                        file_name = str(key) + ".txt"
                        path = os.path.join(os.getcwd(), "optimization", str(id), source, file_name)
                        logger.debug("Path where the data is stored" + str(path))
                        # dataset = dataset.split(",")
                        if os.path.isfile(path):
                            os.remove(path)
                        logger.debug("This is the path to open: "+str(path))
                        with open(path, 'w') as outfile:
                            # outfile.write('\n'.join(str(dataset)))
                            outfile.writelines(str(i) + '\n' for i in data)
                else:
                    logger.debug("No data in " + str(key))
    return 1

def delete_data(id, registry_file, source):
    try:
        dir = os.path.join(os.getcwd(), "utils", str(id))
        if not os.path.exists(dir):
            return "Id not existing"
        else:
            registry = os.path.join(dir, registry_file)
            if os.path.exists(registry):
                os.remove(registry)
            dir_files = os.listdir(dir)
            if dir_files is not None and len(dir_files) == 0:
                os.rmdir(dir)
            path = os.path.join(os.getcwd(), "optimization", str(id), source)
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
            path = os.path.join(os.getcwd(), "optimization", str(id))
            if os.path.exists(path):
                dir_files = os.listdir(path)
                if dir_files is not None and len(dir_files) == 0:
                    os.rmdir(path)
            return "success"
    except Exception as e:
        logger.error(e)
        return "error"

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

def delete_file_registry(id):  # noqa: E501
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
        #dataset = MQTTInputSource.from_dict(connexion.request.get_json())  # noqa: E501
        dataset = connexion.request.get_json()
        logger.info("This is the dictionary: " + str(dataset))

        # check if the file exists
        dir = os.path.join(os.getcwd(), "utils", str(id))
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
    else:
        return 'Data is not in json format'

def file_input_source(File_Input_Source):  # noqa: E501
    """Creates a new data source as input

     # noqa: E501

    :param File_Input_Source: Dataset submitted to the framework
    :type File_Input_Source: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        #File_Input_Source = FileInputSource.from_dict(connexion.request.get_json())  # noqa: E501
        File_Input_Source = connexion.request.get_json()

        try:
            id = utils.create_and_get_ID()
            dir_data = os.path.join(os.getcwd(), "optimization", str(id),"file")
            if not os.path.exists(dir_data):
                os.makedirs(dir_data)
            dir_data = os.path.join(os.getcwd(), "utils", str(id))
            if not os.path.exists(dir_data):
                os.makedirs(dir_data)
        except Exception as e:
            logger.error(e)

        # saves the registry into the new folder
        path = os.path.join(os.getcwd(), "utils", str(id), "Input.registry.file")
        with open(path, 'w') as outfile:
            json.dump(File_Input_Source, outfile, ensure_ascii=False)
            logger.info("registry/input saved into memory")

        #with open(path, 'r') as file:
        input_all=File_Input_Source

        for header in input_all:
            logger.debug("Headers: "+ str(header))
            input = input_all[header]
            if input:
                logger.debug(header + " present")
                if header == "generic":
                    for v in input:
                        if "file" and "name" in v.keys():
                            dataset = v["file"]
                            name = v["name"]
                            file_name = str(name) + ".txt"
                            logger.debug("This is the file name for generic: " + str(file_name))
                            path = os.path.join(os.getcwd(), "optimization", str(id),"file", file_name)
                            logger.debug("Path where the data is stored" + str(path))
                            # dataset = dataset.split(",")
                            with open(path, 'w') as outfile:
                                outfile.writelines(str(i) + '\n' for i in dataset)
                            logger.info("input data saved into memory: " + str(file_name))
                else:
                    for key in input:
                        dataset = input[key]
                        logger.debug("Data in "+str(key)+" is " + str(dataset))
                        if dataset is not None:
                            logger.debug("Type of "+str(key)+str(type(key)))
                            logger.debug("Type of dataset" + str(type(dataset)))
                            #logger.debug("Size of dataset" + str(len(dataset)))
                            """if "soc_value" in str(key):
                                logger.debug("soc_value")
                            elif "SoC_Value" in str(key):
                                logger.debug("SoC_Value")
                            elif "so_c_value" in str(key):
                                logger.debug("so_c_value")
                            else:
                                logger.debug("key: "+str(key))"""

                            if "meta" in key:
                                file_name = str(header) + "_" + str(key) + ".txt"
                                path = os.path.join(os.getcwd(), "optimization", str(id),"file", file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                # dataset = dataset.split(",")
                                with open(path, 'w') as outfile:
                                    outfile.writelines(dataset)
                            elif "SoC_Value" in key:
                                file_name = str(key) + ".txt"
                                path = os.path.join(os.getcwd(), "optimization", str(id),"file", file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                # dataset = dataset.split(",")
                                with open(path, 'w') as outfile:
                                    outfile.write(str(dataset))
                            else:
                                file_name = str(key) + ".txt"
                                path = os.path.join(os.getcwd(), "optimization", str(id),"file", file_name)
                                logger.debug("Path where the data is stored" + str(path))
                                # dataset = dataset.split(",")
                                with open(path, 'w') as outfile:
                                    #outfile.write('\n'.join(str(dataset)))
                                    outfile.writelines(str(i) + '\n' for i in dataset)
                            logger.info("input data saved into memory: " + str(file_name))
                        else:
                            logger.debug("No data in "+str(key))

        return jsonify({'Data-Source-Id':str(id)})
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
    data = ""
    dir = os.path.join(os.getcwd(), "utils", str(id))
    try:
        if not os.path.exists(dir):
            return "Id not existing"
        else:
            file_registry = os.path.join(dir, "Input.registry.file")
            if os.path.exists(file_registry):
                with open(file_registry, "r") as infile:
                    file_data = infile.readlines()
                    data = "File registry = " + file_data
            mqtt_registry = os.path.join(dir, "Input.registry.mqtt")
            if os.path.exists(mqtt_registry):
                with open(mqtt_registry, "r") as infile:
                    mqtt_data = infile.readlines()
                    data = data + "\n" + mqtt_data
    except Exception as e:
        logger.error("error reading registry "+str(e))
        data = "error"
    return data

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
        #dataset = MQTTInputSource.from_dict(connexion.request.get_json())  # noqa: E501
        dataset = connexion.request.get_json()
        logger.info("This is the dictionary: " + str(dataset))

        # check if the file exists
        dir = os.path.join(os.getcwd(), "utils", str(id))
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
                        data[header] = dataset[header]
                    readfile.seek(0)
                    json.dump(data, readfile)
                    readfile.truncate()
                logger.info("data source saved into memory")
            else:
                # saves the registry into the new folder
                # saves the registry into the new folder
                with open(dir_file, 'w') as outfile:
                    json.dump(dataset, outfile, ensure_ascii=False)
                logger.info("data source saved into memory")

            #store_data(dataset, id, "mqtt")
            return "Data source registered"
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
            dir_data = os.path.join(os.getcwd(), "optimization", str(id), "mqtt")
            if not os.path.exists(dir_data):
                os.makedirs(dir_data)
        except Exception as e:
            logger.error(e)

        # saves the registry into the new folder
        path = os.path.join(os.getcwd(), "utils", str(id), "Input.registry.mqtt")
        with open(path, 'w') as outfile:
            json.dump(MQTT_Input_Source, outfile, ensure_ascii=False)
        logger.info("registry/input saved into memory")

        return jsonify({'Data-Source-Id':str(id)})
    else:
        return 'Data is not in json format'
