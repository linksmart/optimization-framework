"""
Created on Aug 10 14:01 2018

@author: nishit
"""
import json
import logging
import random

import time

import math
from senml import senml

from IO.dataPublisher import DataPublisher

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class MockGenericDataPublisher(DataPublisher):

    def __init__(self, config, mock_params):
        topic_params = mock_params["mqtt_topic"]
        pub_frequency = mock_params["pub_frequency_sec"]
        super().__init__(False, topic_params, config, pub_frequency)
        self.generic_name = mock_params["section"]
        self.length = mock_params["horizon_steps"]
        self.delta_time = mock_params["delta_time_sec"]
        self.source = "random"
        if "mock_source" in mock_params.keys():
            self.source = mock_params["mock_source"]
        if self.source == "file":
            file_path = mock_params["mock_file_path"]
            self.file_lines = self.read_file_data(file_path)
            self.file_index = 0
            self.file_length = len(self.file_lines)
        else:
            self.rand_min = mock_params["mock_random_min"]
            self.rand_max = mock_params["mock_random_max"]
            self.data_type = mock_params["mock_data_type"]

    def get_data(self):
        meas_list = []
        current_time = int(math.floor(time.time()))
        if self.source == "file":
            vals = self.get_file_line()
            logger.debug("Length: " + str(self.length))
            if not self.length==1:
                logger.debug("Length vals: " + str(len(vals)))
                if len(vals) < self.length:
                    logger.error(str(self.generic_name) + " mock file has invalid data. Less values than horizon_step")
                    return None
        else:
            vals = self.get_random_floats()
            logger.debug("Vals: "+str(vals))

        logger.debug("Length: " + str(self.length))
        for index in range(self.length):
            meas = senml.SenMLMeasurement()
            meas.value = vals[index]
            meas.time = int(current_time)
            meas.name = self.generic_name
            meas_list.append(meas)
            current_time += self.delta_time
        doc = senml.SenMLDocument(meas_list)
        val = doc.to_json()
        val = json.dumps(val)
        logger.debug("Sent MQTT:" + str(val))
        return val

    def read_file_data(self, file_path):
        with open(file_path, "r") as f:
            file_lines = f.readlines()
        logger.debug("file_lines: "+str(file_lines))
        return file_lines

    def get_file_line(self):
        try:
            if self.file_index >= self.file_length:
                self.file_index = 0
            line = self.file_lines[self.file_index:(self.file_index + self.length)]
            logger.debug("line: "+str(line))
            if self.length > 0:
                logger.debug("Entered in loop")
                if not ";" in line:
                    vals=[]
                    for val in line:
                        vals.extend(val.strip().split("\\n"))

                    counter=0
                    for val in vals:
                        if "," in val:
                            new_value=float(val.replace(",", "."))
                            vals[counter]=str(new_value)
                        counter +=1
                    logger.debug("vals: " + str(vals))
                    vals = [float(val) for val in vals]
                    logger.debug("vals: " + str(vals))
                else:
                    logger.debug("Entered in ;")
                    vals = []
                    for val in line:
                        vals.extend(val.strip().split(";"))
                    logger.debug("vals: "+str(vals))
            #else:
                #vals=[]
                #logger.debug("len of line "+str(len(line)))
                #for val in line:
                    #vals.extend(val.strip().split("\\n"))
                #logger.debug("first vals: "+str(vals))
                #counter = 0
                #for val in vals:
                    #if "," in val:
                        #logger.debug("value with comma: "+str(val))
                        #new_value = float(val.replace(",", "."))
                        #logger.debug("new_value: "+str(new_value))
                        #vals[counter]= str(new_value)
                        #logger.debug("vals intern: "+str(vals))
                    #counter += 1

                #logger.debug("vals: " + str(vals))
                #vals = [float(val) for val in vals]
                #logger.debug("vals: " + str(vals))

            self.file_index = self.length + self.file_index
            return vals
        except Exception as e:
            logger.error("file line read exception "+str(e))

    def get_random_floats(self):
        if self.data_type == "float":
            return [round(random.uniform(self.rand_min, self.rand_max), 6) for _ in range(self.length)]
        else:
            return [random.randrange(self.rand_min, self.rand_max+1) for _ in range(self.length)]
