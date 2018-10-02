"""
Created on Aug 13 11:03 2018

@author: nishit
"""
import json
import logging
from abc import ABC, abstractmethod

from senml import senml

from IO.dataReceiver import DataReceiver

logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__file__)

class BaseDataReceiver(DataReceiver, ABC):

    def __init__(self, internal, topic_params, config, generic_name, id):
        super().__init__(internal, topic_params, config, id=id)
        self.generic_name = generic_name

    def on_msg_received(self, payload):
        senml_data = json.loads(payload)
        formated_data = self.add_formated_data(senml_data)
        self.data.update(formated_data)
        self.data_update = True
        logger.debug("generic data received")

    def add_formated_data(self, json_data):

        logger.debug("add formatted data json: "+str(json_data))
        json_data=json_data["e"][0]
        logger.debug("add formatted data json [e][0]: "+str(json_data))
        doc = None
        try:
            doc = senml.SenMLDocument.from_json(json_data)
            logger.debug("SENMl: "+str(doc))
        except Exception as e:
            pass
        logger.debug("add formatted data: "+str(doc))
        if not doc:
            logger.debug("no doc")
            try:
                meas = senml.SenMLMeasurement.from_json(json_data)
                doc = senml.SenMLDocument([meas])
                logger.debug("new doc: "+str(doc))
            except Exception as e:
                pass
        if doc:
            logger.debug("doc: "+str(json.dumps(doc.to_json())))
            base_data = doc.base
            logger.debug("base data: "+str(base_data))
            #e=doc.e
            #logger.debug("doc e: "+str(e))
            bn, bu = None, None
            if base_data:
                bn = base_data.name
                bu = base_data.unit
            data = {}
            index = {}
            logger.debug("doc.measurement: "+str(doc.measurements))
            for meas in doc.measurements:
                n = meas.name
                u = meas.unit
                v = meas.value
                if not u:
                    u = bu
                    logger.debug("unit: "+str(u))
                if bn and n and bn != n:
                    n = bn + n
                    logger.debug("name bn + n: " + str(n))
                if not n:
                    if not bn:
                        n=self.generic_name
                        logger.debug("name generic name: "+str(n))
                    else:
                        n = bn
                        logger.debug("name bn: " + str(n))
                try:
                    logger.debug("Generic name " + str(self.generic_name) + " exists")
                    v = self.unit_value_change(v, u)
                    logger.debug("value after units change: " + str(v))
                    if n not in index.keys():
                        index[n] = None
                    if n not in data.keys():
                        data[n] = {}
                    data[n][index[n]] = v
                    logger.debug("data[n][index[n]] : " + str(data[n][index[n]]))
                    #index[n] += 1
                    """if n == self.generic_name:
                        logger.debug("Generic name "+str(self.generic_name)+" exists")
                        v = self.unit_value_change(v, u)
                        logger.debug("value after units change: "+str(v))
                        if n not in index.keys():
                            index[n] = None
                        if n not in data.keys():
                            data[n] = {}
                        data[n][index[n]] = v
                        logger.debug("data[n][index[n]] : " + str(data[n][index[n]]))
                        index[n] += 1"""
                except Exception as e:
                    logger.error("error "+str(e)+"  n = "+str(n))
            logger.debug("data: "+str(data))
            return data
        return {}

    @abstractmethod
    def unit_value_change(self, value, unit):
        pass