import connexion
import logging, os
from flask import json
import six

from optimization.utils import Utils
from swagger_server.models.input_source import InputSource  # noqa: E501
from swagger_server.models.output_source import OutputSource  # noqa: E501
from swagger_server import util


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)
utils = Utils()

def getFilePath(dir, file_name):
    # print(os.path.sep)
    # print(os.environ.get("HOME"))
    project_dir = os.path.dirname(os.path.realpath(__file__))
    data_file = os.path.join("/usr/src/app", dir, file_name)
    return data_file

def delete_registry_input(id):  # noqa: E501
    """Deletes the registration of the framework

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return 'do some magic!'


def delete_registry_output(id):  # noqa: E501
    """Deletes the registration output of the framework

     # noqa: E501

    :param id: Name of the registry to be deleted
    :type id: str

    :rtype: None
    """
    return 'do some magic!'



def input_source(Input_Source):  # noqa: E501
    """Creates a new data source as input

     # noqa: E501

    :param InputSource: Data source to be created
    :type InputSource: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        logger.info("registry/input started")
        Input_Source = InputSource.from_dict(connexion.request.get_json())  # noqa: E501
        logger.info("This is the dictionary: " + Input_Source.to_str())
        # logger.info("This is the photovoltaic: "+Output_Source.photovoltaic.to_str())

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
        # Writes the registry/output to a txt file in ordner utils
        path = getFilePath("utils", "Input.registry")
        with open(path, 'w') as outfile:
            json.dump(Input_Source, outfile, ensure_ascii=False)
        logger.info("registry/input saved into memory")
        id = utils.create_and_get_ID()
        path = getFilePath("utils", "registry.id")
        with open(path, 'w') as outfile:
            outfile.write(id)
        return 'Data source Id: ' + str(id)
    else:
        return 'Data is not in json format'




def output_source(Output_Source):  # noqa: E501
    """Creates a new data source as ouput

     # noqa: E501

    :param OutputSource: Output data source to be created
    :type OutputSource: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        logger.info("registry/output started")
        Output_Source = OutputSource.from_dict(connexion.request.get_json())  # noqa: E501

        logger.info("This is the dictionary: "+ Output_Source.to_str() )
        #logger.info("This is the photovoltaic: "+Output_Source.photovoltaic.to_str())

        #ToDo Error checklist
        # if file is true then mqtt is false
        # limitation of qos
        # topic just base name
        # check if there is another name other than host
        # check with the model. Each output variable of the model should have a definition here *******IMPORTANT**************
        # Check for nontype objects
        try:
            ess=Output_Source.ess.to_dict()
            logger.info(str(Output_Source.ess.to_dict()))

            #logger.info("ESS output: "+str(ess["p_ess_output"]))
            #logger.info("ESS ouput file: "+str(ess["p_ess_output"]["file"]))
            #logger.info("ESS ouput mqtt: " + str(ess["p_ess_output"]["mqtt"]))
            #logger.info("ESS ouput mqtt url: " + str(ess["p_ess_output"]["mqtt"]["url"]))
            #logger.info("ESS ouput mqtt topic: " + str(ess["p_ess_output"]["mqtt"]["topic"]))
            #logger.info("ESS ouput mqtt qos: " + str(ess["p_ess_output"]["mqtt"]["qos"]))
            #logger.info("Not: "+str(not ess["p_ess_output"]["mqtt"]["url"]))
            #logger.info("Isspace: " + str(ess["p_ess_output"]["mqtt"]["url"].isspace()))

        except Exception as e:
            logger.info("This error")
            logger.error(e)

        """try:
            check=error_check_output_ambiguity(Output_Source)
            if check != 0:
                message = "Definition Error "+ check +": File and MQTT options chosen at the same time"
                logger.error(message)
                return message
        except Exception as e:
            logger.error(e)"""
        #Writes the registry/output to a txt file in ordner utils
        path = getFilePath("utils", "Output.registry")
        with open(path, 'w') as outfile:
            json.dump(Output_Source, outfile, ensure_ascii=False)
        logger.info("registry/output saved into memory")


    return 'Operation succeded'


def error_check_output_ambiguity(object):
    ess=object.ess.to_dict()
    if (ess["p_ess_output"]["mqtt"]["host"] or ess["p_ess_output"]["mqtt"]["host"].isspace()) and str(ess["p_ess_output"]["file"]) == "True":
        return "ess"

    grid=object.grid.to_dict()
    if (grid["p_grid_export_output"]["mqtt"]["host"] or grid["p_grid_export_output"]["mqtt"]["host"].isspace()) and str(grid["p_grid_export_output"]["file"]) == "True":
        return "grid"
    elif (grid["p_grid_import_output"]["mqtt"]["host"] or grid["p_grid_import_output"]["mqtt"]["host"].isspace()) and str(grid["p_grid_import_output"]["file"]) == "True":
        return "grid"
    elif (grid["q_grid_export_output"]["mqtt"]["host"] or grid["q_grid_export_output"]["mqtt"]["host"].isspace()) and str(grid["q_grid_export_output"]["file"]) == "True":
        return "grid"
    elif (grid["q_grid_import_output"]["mqtt"]["host"] or grid["q_grid_import_output"]["mqtt"]["host"].isspace()) and str(grid["q_grid_import_output"]["file"]) == "True":
        return "grid"

    pv = object.photovoltaic.to_dict()
    if (pv["p_pv_output"]["mqtt"]["host"] or pv["p_pv_output"]["mqtt"]["host"].isspace()) and str(pv["p_pv_output"]["file"]) == "True":
        return "photovoltaic"
    elif (pv["q_pv_output"]["mqtt"]["host"] or pv["q_pv_output"]["mqtt"]["host"].isspace()) and str(pv["q_pv_output"]["file"]) == "True":
        return "photovoltaic"
    else:
        return 0

def error_check_input(object):
    load = object.load.to_dict()
    if (str(load["internal_forecast"]) == "True"):
        if (not (load["p_load"] or load["q_load"])):
            return "load : P_Load or Q_Load empty"
        elif (load["p_load"]["mqtt"] is None and load["p_load"]["file"] is None) or \
                ((load["p_load"]["mqtt"]["host"] or load["p_load"]["mqtt"]["host"].isspace())
                 and str(load["p_load"]["file"]) == "True"):
            return "load : P_Load is empty OR P_Load File and MQTT options chosen at the same time"
        elif (load["q_load"] is not None) and \
                (load["q_load"]["mqtt"] is None and load["q_load"]["file"] is None) and\
                ((load["q_load"]["mqtt"]["host"] or load["q_load"]["mqtt"]["host"].isspace()) and str(load["q_load"]["file"]) == "True"):
            return "load : Q_Load is empty OR Q_Load File and MQTT options chosen at the same time"

    ess = object.ess.to_dict()
    if (ess["soc_value"]["mqtt"] is not None and ess["soc_value"]["value_percent"] is not None) and \
            (ess["soc_value"]["mqtt"]["host"] or ess["soc_value"]["mqtt"]["host"].isspace()) and \
            str(ess["soc_value"]["value_percent"]) == "True":
        return "ESS : SoC_Value is empty OR value_percent and MQTT options chosen at the same time"

    pv = object.photovoltaic.to_dict()
    if (str(pv["internal_forecast"]) == "True"):
        if (not (pv["p_pv"])):
            return "photovoltaic : P_PV empty"
        elif (pv["p_pv"]["mqtt"]["host"] or pv["p_pv"]["mqtt"]["host"].isspace()) and str(
                pv["p_pv"]["file"]) == "True":
            return "photovoltaic : P_PV File and MQTT options chosen at the same time"

    return 0
